import logging
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from app.services.supabase import pb

logger = logging.getLogger(__name__)

# Namespace for deterministic prediction UUID generation
PREDICTION_NAMESPACE = uuid.UUID('23456789-2345-6789-2345-678923456789')

def _parse_date(ts_str: Optional[str]) -> Optional[datetime]:
    if not ts_str:
        return None
    try:
        clean_date = ts_str.replace("T", " ").split(".")[0].replace("Z", "")
        return datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception:
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            return None

def _get_date_string(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")

async def generate_predictions_for_user(user_id: str, token: str) -> List[Dict[str, Any]]:
    """
    Analyzes historical data to generate predictions.
    Saves/updates predictions in the user_predictions table.
    """
    predictions = []
    now_utc = datetime.now(timezone.utc)
    today_str = _get_date_string(now_utc)
    
    # ─── 1. WIND DOWN RITUAL SKIPS (FRIDAYS) ───
    try:
        since_60d = (now_utc - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")
        wind_downs = await pb.list_records(
            "wind_down_rituals",
            token=token,
            params={"filter": f'user_id="{user_id}" && created >= "{since_60d}"', "perPage": 200}
        )
        wd_items = wind_downs.get("items") or []
        wd_dates = set()
        for wd in wd_items:
            dt = _parse_date(wd.get("created"))
            if dt:
                wd_dates.add(_get_date_string(dt))
        
        # Count Fridays in past 60 days
        friday_dates = []
        curr = now_utc - timedelta(days=60)
        while curr < now_utc:
            if curr.weekday() == 4: # Friday
                friday_dates.append(_get_date_string(curr))
            curr += timedelta(days=1)
            
        if len(friday_dates) >= 3:
            skipped_fridays = [f for f in friday_dates if f not in wd_dates]
            skip_rate = len(skipped_fridays) / len(friday_dates)
            if skip_rate >= 0.66:
                # Predict for the next upcoming Friday
                days_ahead = (4 - now_utc.weekday()) % 7
                if days_ahead == 0 and now_utc.hour >= 20: # it's Friday night already, target next week
                    days_ahead = 7
                target_friday = now_utc + timedelta(days=days_ahead)
                target_date_str = _get_date_string(target_friday)
                
                predictions.append({
                    "prediction_type": "wind_down_skip_friday",
                    "prediction_text": "You usually skip Wind Down on Fridays.",
                    "target_date": target_date_str,
                    "confidence_score": int(skip_rate * 100),
                    "metadata": {
                        "total_fridays_evaluated": len(friday_dates),
                        "skipped_fridays_count": len(skipped_fridays)
                    }
                })
    except Exception as e:
        logger.warning("Prediction Engine: failed to evaluate wind_down_skip_friday: %s", e)

    # ─── 2. CHALLENGING TOMORROW ───
    try:
        since_14d = (now_utc - timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")
        moods_resp = await pb.list_records(
            "mood_logs",
            token=token,
            params={"filter": f'user_id="{user_id}" && created >= "{since_14d}"', "sort": "-created", "perPage": 50}
        )
        mood_items = moods_resp.get("items") or []
        
        journals_resp = await pb.list_records(
            "journal_entries",
            token=token,
            params={"filter": f'user_id="{user_id}" && created >= "{since_14d}"', "sort": "-created", "perPage": 50}
        )
        journal_items = journals_resp.get("items") or []
        
        # Check today's check-ins / logs
        today_moods = [m for m in mood_items if _get_date_string(_parse_date(m.get("created"))) == today_str]
        today_journals = [j for j in journal_items if _get_date_string(_parse_date(j.get("created"))) == today_str]
        
        has_negative_indicator = False
        reason = ""
        confidence = 50
        
        # Check today's mood level
        if today_moods:
            min_mood = min(int(m.get("level", 5)) for m in today_moods)
            if min_mood < 5:
                has_negative_indicator = True
                reason = "low_mood_today"
                confidence = 85
                
            # Check negative emotions
            for m in today_moods:
                emotions = [e.lower() for e in (m.get("emotions") or [])]
                negatives = {"stressed", "anxious", "sad", "exhausted", "lonely", "frustrated"}
                matching = negatives.intersection(emotions)
                if matching:
                    has_negative_indicator = True
                    reason = "negative_emotions_today"
                    confidence = max(confidence, 70)
                    
        # Check today's journal text
        if today_journals:
            for j in today_journals:
                txt = (j.get("content") or "").lower()
                neg_words = ["stressed", "anxious", "sad", "hopeless", "exhausted", "tired", "difficult", "struggled", "pain"]
                if any(w in txt for w in neg_words):
                    has_negative_indicator = True
                    reason = "stressed_journal_today"
                    confidence = max(confidence, 65)

        # Check declining trend over past 7 days
        if len(mood_items) >= 4:
            # Get average level of first 2 vs previous 4
            recent_moods = [int(m.get("level", 5)) for m in mood_items[:2]]
            older_moods = [int(m.get("level", 5)) for m in mood_items[2:6]]
            if recent_moods and older_moods:
                avg_recent = sum(recent_moods) / len(recent_moods)
                avg_older = sum(older_moods) / len(older_moods)
                if avg_older - avg_recent >= 1.5:
                    has_negative_indicator = True
                    reason = "declining_mood_trend"
                    confidence = max(confidence, 75)

        if has_negative_indicator:
            target_date_str = _get_date_string(now_utc + timedelta(days=1))
            predictions.append({
                "prediction_type": "challenging_tomorrow",
                "prediction_text": "Tomorrow may be challenging.",
                "target_date": target_date_str,
                "confidence_score": confidence,
                "metadata": {"trigger_reason": reason}
            })
    except Exception as e:
        logger.warning("Prediction Engine: failed to evaluate challenging_tomorrow: %s", e)

    # ─── 3. ACTIVITY MOOD BOOST ───
    try:
        since_60d = (now_utc - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")
        mornings = await pb.list_records(
            "morning_rituals",
            token=token,
            params={"filter": f'user_id="{user_id}" && created >= "{since_60d}"', "perPage": 200}
        )
        morning_items = mornings.get("items") or []
        
        # Group morning rituals by date
        activity_by_date = {}
        for mr in morning_items:
            dt = _parse_date(mr.get("created"))
            if dt:
                date_str = _get_date_string(dt)
                act = mr.get("activity_type")
                if act:
                    activity_by_date[date_str] = act.strip().lower()
                    
        # Group mood logs by date
        moods_by_date = {}
        for m in mood_items: # uses 14d, let's fetch wider mood range (60d) for activity boost correlation
            dt = _parse_date(m.get("created"))
            if dt:
                date_str = _get_date_string(dt)
                moods_by_date.setdefault(date_str, []).append(int(m.get("level", 5)))
                
        # Fetch 60d mood logs if we haven't already
        moods_60d_resp = await pb.list_records(
            "mood_logs",
            token=token,
            params={"filter": f'user_id="{user_id}" && created >= "{since_60d}"', "perPage": 200}
        )
        for m in (moods_60d_resp.get("items") or []):
            dt = _parse_date(m.get("created"))
            if dt:
                date_str = _get_date_string(dt)
                moods_by_date.setdefault(date_str, []).append(int(m.get("level", 5)))
                
        # Calculate daily averages
        daily_avg_mood = {d: sum(levels)/len(levels) for d, levels in moods_by_date.items()}
        
        # Core correlation
        activities = set(activity_by_date.values())
        best_activity = None
        best_boost = 0.0
        best_sample_size = 0
        
        for act in activities:
            if not act or act == "none" or act == "skip":
                continue
            # Filter days when this activity was done
            act_days = [d for d, a in activity_by_date.items() if a == act]
            if len(act_days) >= 3:
                # Average mood on these days
                mood_on_act_days = [daily_avg_mood[d] for d in act_days if d in daily_avg_mood]
                # Average mood on other days
                other_days = [d for d in daily_avg_mood if d not in act_days]
                mood_on_other_days = [daily_avg_mood[d] for d in other_days]
                
                if len(mood_on_act_days) >= 2 and mood_on_other_days:
                    avg_act = sum(mood_on_act_days) / len(mood_on_act_days)
                    avg_other = sum(mood_on_other_days) / len(mood_on_other_days)
                    boost = avg_act - avg_other
                    if boost >= 1.2: # minimum 1.2 points boost
                        if boost > best_boost:
                            best_boost = boost
                            best_activity = act
                            best_sample_size = len(mood_on_act_days)

        if best_activity:
            confidence = min(95, int(50 + best_boost * 25))
            target_date_str = today_str # applies to today/ongoing
            
            # Format nicely
            act_label = best_activity.replace("-", " ").replace("_", " ").lower()
            predictions.append({
                "prediction_type": "activity_mood_boost",
                "prediction_text": f"You tend to feel energized after {act_label}.",
                "target_date": target_date_str,
                "confidence_score": confidence,
                "metadata": {
                    "activity_type": best_activity,
                    "mood_boost_points": round(best_boost, 2),
                    "sample_size_days": best_sample_size
                }
            })
    except Exception as e:
        logger.warning("Prediction Engine: failed to evaluate activity_mood_boost: %s", e)

    # ─── 3. PKG-INTEGRATED STRESSORS AND COPING RECOMMENDATIONS (CIE Phase 4) ───
    try:
        # Fetch user's active knowledge nodes
        nodes_res = await pb.list_records(
            "user_knowledge_nodes",
            token=token,
            params={"filter": f'user_id="{user_id}" && is_archived=false && confidence>=0.4', "perPage": 50}
        )
        pkg_nodes = nodes_res.get("items") or []

        # Find active stressors
        stressors = [n for n in pkg_nodes if n.get("node_type") == "stressor"]
        # Find active coping mechanisms
        coping_mechanisms = [n for n in pkg_nodes if n.get("node_type") == "coping"]

        # Fetch recent journal mentions of stressors in the last 7 days
        since_7d = (now_utc - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        mentions_res = await pb.list_records(
            "user_entity_mentions",
            token=token,
            params={"filter": f'user_id="{user_id}" && created_at>="{since_7d}"', "perPage": 100}
        )
        mentions = mentions_res.get("items") or []
        mentioned_node_ids = {m.get("node_id") for m in mentions if m.get("node_id")}

        # Check if any stressors were mentioned in last 7 days
        for str_node in stressors:
            nid = str_node.get("id")
            if nid in mentioned_node_ids:
                label = str_node.get("label", "").lower()
                m_count = sum(1 for m in mentions if m.get("node_id") == nid)
                confidence = min(90, int(60 + m_count * 5))
                predictions.append({
                    "prediction_type": "pkg_stressor_trigger",
                    "prediction_text": f"Recent mentions of '{label}' suggest a potential anxiety trigger or challenge ahead.",
                    "target_date": today_str,
                    "confidence_score": confidence,
                    "metadata": {
                        "stressor_label": label,
                        "recent_mention_count": m_count
                    }
                })

        # Recommend active coping mechanism if not mentioned in last 3 days
        since_3d = (now_utc - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        mentions_3d = [m for m in mentions if m.get("created_at") >= since_3d]
        mentioned_3d_ids = {m.get("node_id") for m in mentions_3d}

        for cop_node in coping_mechanisms:
            nid = cop_node.get("id")
            if nid not in mentioned_3d_ids:
                label = cop_node.get("label", "").lower()
                predictions.append({
                    "prediction_type": "pkg_coping_recommendation",
                    "prediction_text": f"You haven't practiced your coping strategy '{label}' recently. Doing so might improve your mood regulation.",
                    "target_date": today_str,
                    "confidence_score": 75,
                    "metadata": {
                        "coping_label": label,
                        "days_since_last_mention": 3
                    }
                })
    except Exception as pkg_pred_err:
        logger.warning("Prediction Engine: failed to evaluate PKG predictions: %s", pkg_pred_err)

    # ─── 4. UPSERT INTO DATABASE ───
    upserted_records = []
    for pred in predictions:
        # Generate deterministic UUID so duplicate check works
        deterministic_id = str(uuid.uuid5(PREDICTION_NAMESPACE, f"pred-{user_id}-{pred['prediction_type']}-{pred['target_date']}"))
        
        record = {
            "id": deterministic_id,
            "user_id": user_id,
            "prediction_type": pred["prediction_type"],
            "prediction_text": pred["prediction_text"],
            "target_date": pred["target_date"],
            "confidence_score": pred["confidence_score"],
            "metadata": pred["metadata"],
            "created_at": now_utc.isoformat()
        }
        
        try:
            # Call Supabase upsert using pb helper
            res = await pb.upsert_records(
                "user_predictions",
                records=[record],
                token=token,
                on_conflict="user_id,prediction_type,target_date"
            )
            upserted_records.append(record)
        except Exception as e:
            logger.warning("Prediction Engine: failed to upsert prediction: %s", e)
            
    return upserted_records

async def evaluate_predictions_for_user(user_id: str, token: str) -> Dict[str, Any]:
    """
    Evaluates past-due predictions (where target_date < today and is_correct is NULL)
    against actual logged behavior and computes accuracy statistics.
    """
    now_utc = datetime.now(timezone.utc)
    today_str = _get_date_string(now_utc)
    
    # 1. Fetch pending predictions where target_date is in the past
    try:
        pending_resp = await pb.list_records(
            "user_predictions",
            token=token,
            params={
                "filter": f'user_id="{user_id}" && target_date < "{today_str}" && is_correct = null',
                "perPage": 100
            }
        )
        pending = pending_resp.get("items") or []
    except Exception as e:
        logger.warning("Prediction Engine: failed to retrieve pending predictions: %s", e)
        pending = []

    for pred in pending:
        pid = pred.get("id")
        ptype = pred.get("prediction_type")
        pdate = pred.get("target_date")
        if not pdate:
            continue
            
        pdate_str = pdate[:10]
        is_correct = None
        
        try:
            # ── Evaluation logic ──
            if ptype == "wind_down_skip_friday":
                # Check if they logged a wind down ritual on that Friday
                wd_resp = await pb.list_records(
                    "wind_down_rituals",
                    token=token,
                    params={
                        "filter": f'user_id="{user_id}" && created >= "{pdate_str} 00:00:00" && created <= "{pdate_str} 23:59:59"',
                        "perPage": 1
                    }
                )
                items = wd_resp.get("items") or []
                # Prediction was they WOULD SKIP it. So correctness is true if they DID NOT log a ritual.
                is_correct = len(items) == 0
                
            elif ptype == "challenging_tomorrow":
                # Check if they logged a mood check-in on that date and its level was low (< 6)
                moods_resp = await pb.list_records(
                    "mood_logs",
                    token=token,
                    params={
                        "filter": f'user_id="{user_id}" && created >= "{pdate_str} 00:00:00" && created <= "{pdate_str} 23:59:59"',
                        "perPage": 50
                    }
                )
                items = moods_resp.get("items") or []
                if items:
                    avg_level = sum(int(m.get("level", 5)) for m in items) / len(items)
                    # Correct if mood average was indeed low (< 6)
                    is_correct = avg_level < 6.0
                else:
                    # No mood logged, check journals for negative sentiments
                    journals_resp = await pb.list_records(
                        "journal_entries",
                        token=token,
                        params={
                            "filter": f'user_id="{user_id}" && created >= "{pdate_str} 00:00:00" && created <= "{pdate_str} 23:59:59"',
                            "perPage": 10
                        }
                    )
                    j_items = journals_resp.get("items") or []
                    has_neg = False
                    for j in j_items:
                        txt = (j.get("content") or "").lower()
                        neg_words = ["stressed", "anxious", "sad", "hopeless", "exhausted", "tired", "difficult", "struggled", "pain"]
                        if any(w in txt for w in neg_words):
                            has_neg = True
                    is_correct = has_neg
                    
            elif ptype == "activity_mood_boost":
                # Check if they did the activity and their mood logged on that day was high (>= 7)
                morning_resp = await pb.list_records(
                    "morning_rituals",
                    token=token,
                    params={
                        "filter": f'user_id="{user_id}" && created >= "{pdate_str} 00:00:00" && created <= "{pdate_str} 23:59:59"',
                        "perPage": 5
                    }
                )
                m_items = morning_resp.get("items") or []
                
                # Check if correct activity was done
                target_act = pred.get("metadata", {}).get("activity_type", "")
                did_activity = any((m.get("activity_type") or "").strip().lower() == target_act.strip().lower() for m in m_items)
                
                if did_activity:
                    # Check mood on that day
                    moods_resp = await pb.list_records(
                        "mood_logs",
                        token=token,
                        params={
                            "filter": f'user_id="{user_id}" && created >= "{pdate_str} 00:00:00" && created <= "{pdate_str} 23:59:59"',
                            "perPage": 50
                        }
                    )
                    items = moods_resp.get("items") or []
                    if items:
                        avg_level = sum(int(m.get("level", 5)) for m in items) / len(items)
                        is_correct = avg_level >= 6.5
                    else:
                        is_correct = False
                else:
                    is_correct = False

            if is_correct is not None:
                # Update prediction
                await pb.update_record(
                    "user_predictions",
                    pid,
                    {
                        "is_correct": is_correct,
                        "evaluated_at": now_utc.isoformat()
                    },
                    token=token
                )
        except Exception as eval_err:
            logger.error("Prediction Engine: failed to evaluate prediction %s: %s", pid, eval_err)

    # 2. Compute statistics
    try:
        all_evaluated = await pb.list_records(
            "user_predictions",
            token=token,
            params={
                "filter": f'user_id="{user_id}" && is_correct != null',
                "perPage": 500
            }
        )
        items = all_evaluated.get("items") or []
        total = len(items)
        correct = len([i for i in items if i.get("is_correct") is True])
        accuracy = correct / total if total > 0 else 1.0 # default to 100% if none evaluated yet
        
        return {
            "total_evaluated": total,
            "correct_count": correct,
            "accuracy_rate": accuracy
        }
    except Exception as e:
        logger.warning("Prediction Engine: failed to compute statistics: %s", e)
        return {
            "total_evaluated": 0,
            "correct_count": 0,
            "accuracy_rate": 1.0
        }

async def get_active_predictions_context(user_id: str, token: str) -> str:
    """
    Returns a formatted markdown text summarizing the user's active predictions
    to be injected into ARIA's prompt context.
    """
    try:
        now_utc = datetime.now(timezone.utc)
        today_str = _get_date_string(now_utc)
        
        # Query active predictions
        active_resp = await pb.list_records(
            "user_predictions",
            token=token,
            params={
                "filter": f'user_id="{user_id}" && target_date >= "{today_str}" && is_correct = null',
                "perPage": 10
            }
        )
        items = active_resp.get("items") or []
        if not items:
            return ""
            
        lines = []
        for i in items:
            txt = i.get("prediction_text")
            conf = i.get("confidence_score", 50)
            ptype = i.get("prediction_type", "")
            lines.append(f"- {txt} (Model: {ptype}, Confidence: {conf}%)")
            
        return "\n".join(lines)
    except Exception as e:
        logger.warning("Prediction Engine: failed to fetch context: %s", e)
        return ""
