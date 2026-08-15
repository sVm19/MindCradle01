package online.mindcradle.GlanceWidgets

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.glance.Button
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.action.actionStartActivity
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.appwidget.provideContent
import androidx.glance.background
import androidx.glance.layout.*
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

// MARK: - API Client & Cache Helper

object WidgetDataManager {

    fun getCachedData(context: Context): String? {
        val sharedPrefs = context.getSharedPreferences("mindcradle_widget_prefs", Context.MODE_PRIVATE)
        return sharedPrefs.getString("cached_payload", null)
    }

    fun syncWidgets(context: Context, callback: (Boolean) -> Unit) {
        val sharedPrefs = context.getSharedPreferences("mindcradle_widget_prefs", Context.MODE_PRIVATE)
        val token = sharedPrefs.getString("accessToken", null)

        if (token.isNullOrEmpty()) {
            callback(false)
            return
        }

        CoroutineScope(Dispatchers.IO).launch {
            try {
                // Host loopback URL for Android emulator
                val urlObj = URL("http://10.0.2.2:8000/api/widgets/home")
                val connection = urlObj.openConnection() as HttpURLConnection
                connection.requestMethod = "GET"
                connection.setRequestProperty("Authorization", "Bearer $token")
                connection.connectTimeout = 5000
                connection.readTimeout = 5000

                if (connection.responseCode == 200) {
                    val streamText = connection.inputStream.bufferedReader().use { it.readText() }
                    sharedPrefs.edit().putString("cached_payload", streamText).apply()
                    callback(true)
                } else if (connection.responseCode == 401) {
                    // Invalid token
                    sharedPrefs.edit().remove("accessToken").apply()
                    callback(false)
                } else {
                    callback(false)
                }
            } catch (e: Exception) {
                android.util.Log.w("WidgetDataManager", "Sync failed: " + e.message)
                callback(false)
            }
        }
    }
}

// MARK: - Glance Widgets Definitions

class AriaGlanceWidget : GlanceAppWidget() {
    override suspend fun provideContent(context: Context, id: GlanceId) {
        val jsonStr = WidgetDataManager.getCachedData(context)
        val isLoggedOut = context.getSharedPreferences("mindcradle_widget_prefs", Context.MODE_PRIVATE).getString("accessToken", null).isNullOrEmpty()

        var ariaMessage = "How are you feeling today?"
        if (jsonStr != null) {
            try {
                val json = JSONObject(jsonStr)
                ariaMessage = json.getJSONObject("aria").optString("message", ariaMessage)
            } catch (e: Exception) { /* parse fallback */ }
        }

        provideContent {
            Column(
                modifier = GlanceModifier
                    .fillMaxSize()
                    .padding(12.dp)
                    .background(ColorProvider(android.graphics.Color.parseColor("#0f0a1c"))),
                verticalAlignment = Alignment.Vertical.CenterVertically,
                horizontalAlignment = Alignment.Horizontal.Start
            ) {
                if (isLoggedOut) {
                    Text(
                        text = "Sign in to MindCradle",
                        style = TextStyle(fontWeight = FontWeight.Bold, color = ColorProvider(android.graphics.Color.WHITE))
                    )
                    Spacer(modifier = GlanceModifier.height(4.dp))
                    Text(
                        text = "Open app to connect with ARIA.",
                        style = TextStyle(color = ColorProvider(android.graphics.Color.GRAY))
                    )
                } else {
                    Text(
                        text = "ARIA",
                        style = TextStyle(fontWeight = FontWeight.Bold, color = ColorProvider(android.graphics.Color.parseColor("#feba7b")))
                    )
                    Spacer(modifier = GlanceModifier.height(6.dp))
                    Text(
                        text = "\"$ariaMessage\"",
                        style = TextStyle(color = ColorProvider(android.graphics.Color.WHITE))
                    )
                    Spacer(modifier = GlanceModifier.height(8.dp))
                    
                    // Button links dynamically to the mindcradle://aria deep link
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse("mindcradle://aria"))
                    Button(
                        text = "Talk to ARIA",
                        onClick = actionStartActivity(intent)
                    )
                }
            }
        }
    }
}

class JournalGlanceWidget : GlanceAppWidget() {
    override suspend fun provideContent(context: Context, id: GlanceId) {
        val jsonStr = WidgetDataManager.getCachedData(context)
        val isLoggedOut = context.getSharedPreferences("mindcradle_widget_prefs", Context.MODE_PRIVATE).getString("accessToken", null).isNullOrEmpty()

        var prompt = "What's on your mind today?"
        if (jsonStr != null) {
            try {
                val json = JSONObject(jsonStr)
                prompt = json.getJSONObject("journal").optString("prompt", prompt)
            } catch (e: Exception) { /* parse fallback */ }
        }

        provideContent {
            Column(
                modifier = GlanceModifier
                    .fillMaxSize()
                    .padding(12.dp)
                    .background(ColorProvider(android.graphics.Color.parseColor("#0f0a1c"))),
                verticalAlignment = Alignment.Vertical.CenterVertically,
                horizontalAlignment = Alignment.Horizontal.Start
            ) {
                if (isLoggedOut) {
                    Text(
                        text = "MindCradle Journal",
                        style = TextStyle(fontWeight = FontWeight.Bold, color = ColorProvider(android.graphics.Color.WHITE))
                    )
                    Spacer(modifier = GlanceModifier.height(4.dp))
                    Text(
                        text = "Open app to compose entries.",
                        style = TextStyle(color = ColorProvider(android.graphics.Color.GRAY))
                    )
                } else {
                    Text(
                        text = "DAILY JOURNAL",
                        style = TextStyle(fontWeight = FontWeight.Bold, color = ColorProvider(android.graphics.Color.GRAY))
                    )
                    Spacer(modifier = GlanceModifier.height(4.dp))
                    Text(
                        text = prompt,
                        style = TextStyle(color = ColorProvider(android.graphics.Color.WHITE))
                    )
                    Spacer(modifier = GlanceModifier.height(8.dp))

                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse("mindcradle://journal/new"))
                    Button(
                        text = "Write",
                        onClick = actionStartActivity(intent)
                    )
                }
            }
        }
    }
}

class StreakGlanceWidget : GlanceAppWidget() {
    override suspend fun provideContent(context: Context, id: GlanceId) {
        val jsonStr = WidgetDataManager.getCachedData(context)
        val isLoggedOut = context.getSharedPreferences("mindcradle_widget_prefs", Context.MODE_PRIVATE).getString("accessToken", null).isNullOrEmpty()

        var streakCount = 0
        var streakMessage = "Ready for another day?"
        if (jsonStr != null) {
            try {
                val json = JSONObject(jsonStr)
                val streakObj = json.getJSONObject("streak")
                streakCount = streakObj.optInt("days", 0)
                streakMessage = streakObj.optString("message", streakMessage)
            } catch (e: Exception) { /* parse fallback */ }
        }

        provideContent {
            Column(
                modifier = GlanceModifier
                    .fillMaxSize()
                    .padding(12.dp)
                    .background(ColorProvider(android.graphics.Color.parseColor("#0f0a1c"))),
                verticalAlignment = Alignment.Vertical.CenterVertically,
                horizontalAlignment = Alignment.Horizontal.Start
            ) {
                if (isLoggedOut) {
                    Text(
                        text = "Streak",
                        style = TextStyle(fontWeight = FontWeight.Bold, color = ColorProvider(android.graphics.Color.WHITE))
                    )
                } else {
                    Row(verticalAlignment = Alignment.Vertical.CenterVertically) {
                        Text(
                            text = "🔥  ",
                            style = TextStyle(color = ColorProvider(android.graphics.Color.parseColor("#feba7b")))
                        )
                        Text(
                            text = "$streakCount DAYS",
                            style = TextStyle(fontWeight = FontWeight.Bold, color = ColorProvider(android.graphics.Color.WHITE))
                        )
                    }
                    Spacer(modifier = GlanceModifier.height(4.dp))
                    Text(
                        text = streakMessage,
                        style = TextStyle(color = ColorProvider(android.graphics.Color.GRAY))
                    )
                }
            }
        }
    }
}

// MARK: - Glance Receivers

class AriaWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = AriaGlanceWidget()
}

class JournalWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = JournalGlanceWidget()
}

class StreakWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = StreakGlanceWidget()
}

// MARK: - Intent Receiver to trigger refreshes on Auth Synchronization

class WidgetUpdateReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if ("online.mindcradle.action.REFRESH_WIDGETS" == intent.action) {
            val pendingResult = goAsync()
            WidgetDataManager.syncWidgets(context) { success ->
                CoroutineScope(Dispatchers.Main).launch {
                    // Update all widgets
                    AriaGlanceWidget().updateAll(context)
                    JournalGlanceWidget().updateAll(context)
                    StreakGlanceWidget().updateAll(context)
                    pendingResult.finish()
                }
            }
        }
    }
}
