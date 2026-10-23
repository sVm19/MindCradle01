import SwiftUI

@main
struct MindCradleApp: App {
    @State private var currentPath: String = "/"
    
    // Default site endpoint (maps to localized dev port or production site URL)
    let defaultWebURL = URL(string: "http://localhost:5173")!
    
    var body: some Scene {
        WindowGroup {
            NavigationView {
                WebView(url: defaultWebURL, currentPath: $currentPath)
                    .edgesIgnoringSafeArea(.all)
                    .navigationBarHidden(true)
            }
            .onOpenURL { url in
                handleDeepLink(url: url)
            }
        }
    }
    
    private func handleDeepLink(url: URL) {
        guard url.scheme == "mindcradle" else { return }
        
        let host = url.host ?? ""
        let path = url.path
        
        print("iOS Shell: Deep link received: \(url.absoluteString)")
        
        // Map deep link scheme to web app pages
        switch host {
        case "aria":
            currentPath = "/aria"
        case "journal":
            if path == "/new" {
                currentPath = "/journal"
            } else {
                currentPath = "/journal"
            }
        case "mood":
            currentPath = "/mood"
        case "insight":
            currentPath = "/insights"
        case "memory":
            currentPath = "/timeline" // Maps memory widgets to timeline/archive
        case "reflection":
            currentPath = "/journal"
        case "solstice":
            currentPath = "/settings"
        case "settings":
            if path == "/widgets" {
                currentPath = "/settings/widgets"
            } else {
                currentPath = "/settings"
            }
        default:
            currentPath = "/dashboard"
        }
    }
}
