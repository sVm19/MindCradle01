package online.mindcradle

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity

class DeepLinkActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val intent = intent
        val action = intent.action
        val data: Uri? = intent.data

        if (Intent.ACTION_VIEW == action && data != null) {
            val scheme = data.scheme
            val host = data.host ?: ""
            val path = data.path ?: ""

            var targetPath = "/"
            
            if ("mindcradle" == scheme) {
                when (host) {
                    "aria" -> targetPath = "/aria"
                    "journal" -> {
                        targetPath = if (path == "/new") "/journal" else "/journal"
                    }
                    "mood" -> targetPath = "/mood"
                    "insight" -> targetPath = "/insights"
                    "memory" -> targetPath = "/timeline"
                    "reflection" -> targetPath = "/journal"
                    "solstice" -> targetPath = "/settings"
                    "settings" -> {
                        targetPath = if (path == "/widgets") "/settings/widgets" else "/settings"
                    }
                    else -> targetPath = "/dashboard"
                }
            }

            // Launch MainActivity with target route path parameter
            val mainIntent = Intent(this, MainActivity::class.java).apply {
                putExtra("target_path", targetPath)
                addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            }
            startActivity(mainIntent)
        }
        
        finish()
    }
}
