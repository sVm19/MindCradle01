import SwiftUI
import WebKit
import WidgetIntents
import WidgetKit

struct WebView: UIViewRepresentable {
    let url: URL
    @Binding var currentPath: String
    
    // Message handler name matches what the React app dispatches to
    class Coordinator: NSObject, WKScriptMessageHandler, WKNavigationDelegate {
        var parent: WebView
        
        init(_ parent: WebView) {
            self.parent = parent
        }
        
        // Intercept messages posted via window.webkit.messageHandlers.authHandler.postMessage
        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            guard message.name == "authHandler" else { return }
            
            if let jsonString = message.body as? String {
                let sharedDefaults = UserDefaults(suiteName: "group.online.mindcradle")
                
                if jsonString == "null" || jsonString.isEmpty {
                    // Logged out
                    sharedDefaults?.removeObject(forKey: "accessToken")
                    sharedDefaults?.removeObject(forKey: "userEmail")
                    sharedDefaults?.removeObject(forKey: "userId")
                    print("iOS Shell: User logged out, cleared token.")
                } else if let data = jsonString.data(using: .utf8),
                          let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    // Logged in
                    let token = json["token"] as? String ?? ""
                    let email = json["email"] as? String ?? ""
                    let userId = json["userId"] as? String ?? ""
                    
                    sharedDefaults?.set(token, forKey: "accessToken")
                    sharedDefaults?.set(email, forKey: "userEmail")
                    sharedDefaults?.set(userId, forKey: "userId")
                    print("iOS Shell: User logged in, saved token to App Group.")
                }
                
                // Proactively reload home screen widgets to pull fresh data
                WidgetCenter.shared.reloadAllTimelines()
            }
        }
        
        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            print("iOS Shell: WebView loaded successfully.")
        }
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }
    
    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        let controller = WKUserContentController()
        
        // Register coordination handler
        controller.add(context.coordinator, name: "authHandler")
        configuration.userContentController = controller
        
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        webView.allowsBackForwardNavigationGestures = true
        
        return webView
    }
    
    func updateUIView(_ uiView: WKWebView, context: Context) {
        // Handle deep-linking navigation adjustments
        let baseAppURL = "http://localhost:5173" // Vite dev url (or production equivalent)
        let destinationURL = URL(string: baseAppURL + currentPath) ?? url
        
        if uiView.url?.path != destinationURL.path {
            let request = URLRequest(url: destinationURL)
            uiView.load(request)
        }
    }
}
