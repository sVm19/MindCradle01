package online.mindcradle

import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.webkit.JavascriptInterface
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        webView = WebView(this)
        setContentView(webView)

        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.webViewClient = WebViewClient()

        // Bind the JavaScript interface
        webView.addJavascriptInterface(AndroidAuthBridge(this), "AndroidAuthBridge")
        webView.addJavascriptInterface(AndroidWidgetBridge(this), "AndroidWidgetBridge")

        // Load the web app (maps to localhost for local testing, or prod URL)
        val defaultUrl = "http://10.0.2.2:5173" // Android emulator loopback to host port 5173
        
        // Handle deep-linking navigation if activity was launched with a path
        val targetPath = intent.getStringExtra("target_path") ?: ""
        webView.loadUrl(defaultUrl + targetPath)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        val targetPath = intent.getStringExtra("target_path") ?: ""
        if (targetPath.isNotEmpty()) {
            val defaultUrl = "http://10.0.2.2:5173"
            webView.loadUrl(defaultUrl + targetPath)
        }
    }
}

class AndroidWidgetBridge(private val context: Context) {
    @JavascriptInterface
    fun pinWidget(widgetId: String) {
        val appWidgetManager = context.getSystemService(android.appwidget.AppWidgetManager::class.java) ?: return
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            if (appWidgetManager.isRequestPinAppWidgetSupported) {
                val provider = when (widgetId) {
                    "aria" -> android.content.ComponentName(context, "online.mindcradle.GlanceWidgets.AriaWidgetReceiver")
                    "journal" -> android.content.ComponentName(context, "online.mindcradle.GlanceWidgets.JournalWidgetReceiver")
                    else -> android.content.ComponentName(context, "online.mindcradle.GlanceWidgets.StreakWidgetReceiver")
                }
                val pinRunnableIntent = Intent()
                val successCallback = android.app.PendingIntent.getBroadcast(
                    context,
                    0,
                    pinRunnableIntent,
                    android.app.PendingIntent.FLAG_UPDATE_CURRENT or android.app.PendingIntent.FLAG_IMMUTABLE
                )
                appWidgetManager.requestPinAppWidget(provider, null, successCallback)
            }
        }
    }
}

class AndroidAuthBridge(private val context: Context) {

    @JavascriptInterface
    fun syncAuth(jsonString: String) {
        val sharedPrefs = context.getSharedPreferences("mindcradle_widget_prefs", Context.MODE_PRIVATE)
        val editor = sharedPrefs.edit()

        if (jsonString == "null" || jsonString.isEmpty()) {
            editor.remove("accessToken")
            editor.remove("userId")
            editor.remove("userEmail")
            editor.apply()
            android.util.Log.d("AndroidAuthBridge", "Logged out, cleared token.")
        } else {
            try {
                val jsonObject = org.json.JSONObject(jsonString)
                val token = jsonObject.optString("token", "")
                val userId = jsonObject.optString("userId", "")
                val email = jsonObject.optString("email", "")

                editor.putString("accessToken", token)
                editor.putString("userId", userId)
                editor.putString("userEmail", email)
                editor.apply()
                android.util.Log.d("AndroidAuthBridge", "Logged in, synced token.")
            } catch (e: Exception) {
                android.util.Log.e("AndroidAuthBridge", "Error parsing auth sync json: " + e.message)
            }
        }
        
        // Broadcast intent to update Glance widgets
        val intent = Intent("online.mindcradle.action.REFRESH_WIDGETS")
        context.sendBroadcast(intent)
    }
}
