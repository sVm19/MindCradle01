import logging
import hashlib
import math
from typing import Dict, List, Optional, Any
from app.services.supabase import pb, _get_client, _execute_query

logger = logging.getLogger(__name__)

def calculate_p_value(conversions_a: int, total_a: int, conversions_b: int, total_b: int) -> float:
    """
    Calculate Z-Test two-tailed p-value for the difference in proportions.
    Returns 1.0 if insufficient data or divide-by-zero occurs.
    """
    if total_a == 0 or total_b == 0:
        return 1.0
        
    p_a = conversions_a / total_a
    p_b = conversions_b / total_b
    if p_a == p_b:
        return 1.0
        
    # Pooled conversion rate
    p_pool = (conversions_a + conversions_b) / (total_a + total_b)
    if p_pool == 0 or p_pool == 1:
        return 1.0
        
    # Standard Error
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / total_a + 1 / total_b))
    if se == 0:
        return 1.0
        
    z_score = (p_b - p_a) / se
    
    # Standard normal cumulative distribution function (CDF) approximation via math.erf
    cdf = lambda x: 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
    p_val = 2.0 * (1.0 - cdf(abs(z_score)))
    
    return float(p_val)


class GrowthEngine:
    """Service to manage product growth experiments, user assignments, and telemetry funnels."""

    async def get_active_assignments(self, user_id: str, token: str) -> List[Dict[str, Any]]:
        """
        Fetch running experiments and stickily assign user to a variant.
        Saves assignments to db to maintain persistence.
        """
        try:
            # 1. Fetch running experiments
            exprs_resp = await pb.list_records(
                "ab_experiments",
                token=token,
                params={"filter": 'status="running"'}
            )
            running_exprs = exprs_resp.get("items") or []
            
            if not running_exprs:
                return []
                
            # 2. Fetch existing assignments
            assign_resp = await pb.list_records(
                "ab_assignments",
                token=token,
                params={"filter": f'user_id="{user_id}"'}
            )
            existing_assigns = {a["experiment_id"]: a for a in (assign_resp.get("items") or [])}
            
            assignments = []
            for expr in running_exprs:
                expr_id = expr["id"]
                expr_name = expr["name"]
                variants = expr["variants"]
                
                # Verify existing assignment
                if expr_id in existing_assigns:
                    assigned_variant = existing_assigns[expr_id]["assigned_variant"]
                else:
                    # Deterministic hashing for sticky, balanced variants allocation
                    hash_input = f"{user_id}:{expr_name}"
                    hash_val = hashlib.md5(hash_input.encode("utf-8")).hexdigest()
                    variant_idx = int(hash_val, 16) % len(variants)
                    assigned_variant = variants[variant_idx]
                    
                    # Store assignment stickily
                    try:
                        await pb.create_record(
                            "ab_assignments",
                            {
                                "user_id": user_id,
                                "experiment_id": expr_id,
                                "assigned_variant": assigned_variant
                            },
                            token=token
                        )
                    except Exception as db_err:
                        logger.error("Failed to persist A/B assignment for user %s: %s", user_id, db_err)
                
                assignments.append({
                    "experiment_id": expr_id,
                    "experiment_name": expr_name,
                    "variant": assigned_variant,
                    "variants": variants
                })
                
            return assignments
        except Exception as e:
            logger.error("Error fetching active assignments: %s", e)
            return []

    async def record_event(self, user_id: str, event_name: str, properties: Dict[str, Any], token: str) -> bool:
        """Record custom growth/telemetry event, auto-tagging active experiment variant context."""
        try:
            # Check if this event relates to active A/B tests to auto-resolve variant context
            assignments = await self.get_active_assignments(user_id, token)
            
            # Map of experiment name to assigned variant
            active_variants = {a["experiment_name"]: a for a in assignments}
            
            experiment_id = None
            variant = None
            
            # Auto-tag based on event context keywords or explicit properties
            if "experiment_name" in properties:
                exp_name = properties["experiment_name"]
                if exp_name in active_variants:
                    experiment_id = active_variants[exp_name]["experiment_id"]
                    variant = active_variants[exp_name]["variant"]
            else:
                # Fallback matching on naming conventions
                for exp_name, details in active_variants.items():
                    if exp_name in event_name or any(exp_name in str(k) for k in properties.keys()):
                        experiment_id = details["experiment_id"]
                        variant = details["variant"]
                        break
                        
            event_data = {
                "user_id": user_id,
                "event_name": event_name,
                "properties": properties,
                "experiment_id": experiment_id,
                "variant": variant
            }
            
            await pb.create_record("growth_events", event_data, token=token)
            return True
        except Exception as e:
            logger.error("Failed to record growth event: %s", e)
            return False

    async def get_experiment_analytics(self, token: str) -> List[Dict[str, Any]]:
        """Calculate conversion metrics, delta improvements, and statistical p-values for all experiments."""
        try:
            # Fetch all experiments
            exprs_resp = await pb.list_records("ab_experiments", token=token)
            experiments = exprs_resp.get("items") or []
            
            # Get event/conversion counts grouped by experiment + variant
            # Note: Since postgrest client is wrapper, we fetch assignments and events to aggregate in python safely
            assigns_resp = await pb.list_records("ab_assignments", token=token, params={"perPage": 10000})
            assignments = assigns_resp.get("items") or []
            
            events_resp = await pb.list_records("growth_events", token=token, params={"perPage": 10000})
            events = events_resp.get("items") or []
            
            analytics = []
            for expr in experiments:
                expr_id = expr["id"]
                expr_name = expr["name"]
                variants = expr["variants"]
                status = expr["status"]
                
                # Calculate sample sizes
                expr_assigns = [a for a in assignments if a["experiment_id"] == expr_id]
                sample_sizes = {}
                for v in variants:
                    sample_sizes[v] = sum(1 for a in expr_assigns if a["assigned_variant"] == v)
                    
                # Group conversions. A conversion is unique users who did a specific action (e.g. ritual completion, click, etc.)
                # Determine conversion event name based on experiment
                conv_event = "morning_ritual_completed" if "morning" in expr_name else "signup_completed"
                if "pricing" in expr_name:
                    conv_event = "subscribed"
                    
                expr_events = [e for e in events if e["experiment_id"] == expr_id]
                conversions = {}
                for v in variants:
                    # Count unique users who completed the target conversion event
                    unique_converts = {e["user_id"] for e in expr_events if e["variant"] == v and e["event_name"] == conv_event}
                    conversions[v] = len(unique_converts)
                    
                # Build variant stats breakdown
                variant_stats = []
                control_rate = 0.0
                treatment_rate = 0.0
                
                # Assume variants[0] is control, variants[1] is treatment
                control_var = variants[0] if len(variants) > 0 else "control"
                treatment_var = variants[1] if len(variants) > 1 else "treatment"
                
                for v in variants:
                    n = sample_sizes.get(v, 0)
                    c = conversions.get(v, 0)
                    rate = float(c / n * 100) if n > 0 else 0.0
                    
                    if v == control_var:
                        control_rate = rate
                    elif v == treatment_var:
                        treatment_rate = rate
                        
                    variant_stats.append({
                        "variant": v,
                        "sample_size": n,
                        "conversions": c,
                        "conversion_rate": round(rate, 2)
                    })
                    
                # Calculate significance Z-Test
                c_a = conversions.get(control_var, 0)
                n_a = sample_sizes.get(control_var, 0)
                c_b = conversions.get(treatment_var, 0)
                n_b = sample_sizes.get(treatment_var, 0)
                
                p_val = calculate_p_value(c_a, n_a, c_b, n_b)
                significant = p_val < 0.05
                improvement = float(treatment_rate - control_rate)
                
                conclusion = "Inconclusive results. Keep running the experiment to accumulate more samples."
                if significant:
                    if improvement > 0:
                        conclusion = f"Significant Winner! Treatment variant outperformed control by {improvement:.1f}% (p = {p_val:.4f})."
                    else:
                        conclusion = f"Control is Winner! Treatment was worse by {-improvement:.1f}% (p = {p_val:.4f})."
                        
                analytics.append({
                    "id": expr_id,
                    "name": expr_name,
                    "description": expr["description"],
                    "status": status,
                    "variants": variant_stats,
                    "p_value": round(p_val, 4),
                    "is_significant": significant,
                    "improvement_delta": round(improvement, 2),
                    "conclusion": conclusion
                })
                
            return analytics
        except Exception as e:
            logger.error("Error compiling experiment analytics: %s", e)
            return []

    async def get_funnel_analytics(self, token: str) -> List[Dict[str, Any]]:
        """Calculate funnel completion rates across all 7 steps of the onboarding/activation funnel."""
        try:
            # 1. Fetch all users
            profiles_resp = await pb.list_records("user_profiles", token=token, params={"perPage": 10000})
            profiles = profiles_resp.get("items") or []
            total_registered = len(profiles)
            
            moods_resp = await pb.list_records("mood_logs", token=token, params={"perPage": 10000})
            mood_users = {m["user_id"] for m in (moods_resp.get("items") or [])}
            
            morn_resp = await pb.list_records("morning_rituals", token=token, params={"perPage": 10000})
            morn_users = {mr["user_id"] for mr in (morn_resp.get("items") or [])}
            
            wind_resp = await pb.list_records("wind_down_rituals", token=token, params={"perPage": 10000})
            wind_users = {wr["user_id"] for wr in (wind_resp.get("items") or [])}
            
            chat_resp = await pb.list_records("ai_conversations", token=token, params={"perPage": 10000})
            chat_users = {c["user_id"] for c in (chat_resp.get("items") or [])}
            
            subscribed_users = {p["user_id"] for p in profiles if p.get("creem_subscription_id") is not None}
            
            events_resp = await pb.list_records("growth_events", token=token, params={"perPage": 10000})
            events = events_resp.get("items") or []
            guest_landings = len({e["id"] for e in events if e["event_name"] == "landing_viewed"})
            
            step1_count = max(total_registered + guest_landings, 1)
            step2_count = total_registered
            step3_count = len(mood_users)
            step4_count = len(morn_users)
            step5_count = len(wind_users)
            step6_count = len(chat_users)
            step7_count = len(subscribed_users)
            
            funnel_steps = [
                {"step": 1, "name": "1. Visited Landing", "count": step1_count, "percent": 100.0},
                {"step": 2, "name": "2. Created Account", "count": step2_count, "percent": round(step2_count / step1_count * 100, 1) if step1_count > 0 else 0.0},
                {"step": 3, "name": "3. Logged First Mood", "count": step3_count, "percent": round(step3_count / step2_count * 100, 1) if step2_count > 0 else 0.0},
                {"step": 4, "name": "4. Completed Morning Focus", "count": step4_count, "percent": round(step4_count / step2_count * 100, 1) if step2_count > 0 else 0.0},
                {"step": 5, "name": "5. Completed Wind Down", "count": step5_count, "percent": round(step5_count / step2_count * 100, 1) if step2_count > 0 else 0.0},
                {"step": 6, "name": "6. Chat with ARIA", "count": step6_count, "percent": round(step6_count / step2_count * 100, 1) if step2_count > 0 else 0.0},
                {"step": 7, "name": "7. Subscribed to Premium", "count": step7_count, "percent": round(step7_count / step2_count * 100, 1) if step2_count > 0 else 0.0}
            ]
            
            return funnel_steps
        except Exception as e:
            logger.error("Error building funnel analytics: %s", e)
            return []

growth_engine = GrowthEngine()
