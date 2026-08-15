import WidgetKit
import SwiftUI

// MARK: - Data Models

struct WidgetResponse: Codable {
    let aria: AriaData
    let journal: JournalData
    let insight: InsightData
    let memory: MemoryData
    let dailyQuestion: QuestionData
    let mood: MoodData
    let habit: HabitData
    let streak: StreakData
    let solstice: SolsticeData
}

struct AriaData: Codable {
    let message: String
    let action: String
}

struct JournalData: Codable {
    let prompt: String
    let action: String
}

struct InsightData: Codable {
    let text: String
    let available: Bool
    let action: String
}

struct MemoryData: Codable {
    let text: String
    let available: Bool
    let action: String
}

struct QuestionData: Codable {
    let text: String
    let action: String
}

struct MoodData: Codable {
    let completed: Bool
    let action: String
}

struct HabitData: Codable {
    let morningCompleted: Bool
    let winddownCompleted: Bool
    let moodCompleted: Bool
    let action: String
}

struct StreakData: Codable {
    let days: Int
    let message: String
    let action: String
}

struct SolsticeData: Codable {
    let message: String
    let available: Bool
    let action: String
}

// MARK: - Timeline Entry

struct WidgetEntry: TimelineEntry {
    let date: Date
    let response: WidgetResponse?
    let isLoggedOut: Bool
}

// MARK: - Network Client

class WidgetNetworkManager {
    static let shared = WidgetNetworkManager()
    
    // API endpoint (points to localhost for development, or production host)
    private let apiURL = URL(string: "http://127.0.0.1:8000/api/widgets/home")!
    
    func fetchWidgetData(completion: @escaping (WidgetResponse?, Bool) -> Void) {
        let sharedDefaults = UserDefaults(suiteName: "group.online.mindcradle")
        
        guard let token = sharedDefaults?.string(forKey: "accessToken"), !token.isEmpty else {
            // No token found -> User is logged out
            completion(nil, true)
            return
        }
        
        var request = URLRequest(url: apiURL)
        request.httpMethod = "GET"
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            guard error == nil, let data = data else {
                completion(nil, false)
                return
            }
            
            // Validate session expiry if backend returns 401
            if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 401 {
                sharedDefaults?.removeObject(forKey: "accessToken")
                completion(nil, true)
                return
            }
            
            do {
                let decoded = try JSONDecoder().decode(WidgetResponse.self, from: data)
                completion(decoded, false)
            } catch {
                print("WidgetKit Network Error: \(error.localizedDescription)")
                completion(nil, false)
            }
        }
        task.resume()
    }
}

// MARK: - Timeline Provider

struct WidgetProvider: TimelineProvider {
    typealias Entry = WidgetEntry
    
    func placeholder(in context: Context) -> WidgetEntry {
        WidgetEntry(date: Date(), response: nil, isLoggedOut: false)
    }
    
    func getSnapshot(in context: Context, completion: @escaping (WidgetEntry) -> Void) {
        let entry = WidgetEntry(date: Date(), response: nil, isLoggedOut: false)
        completion(entry)
    }
    
    func getTimeline(in context: Context, completion: @escaping (Timeline<WidgetEntry>) -> Void) {
        WidgetNetworkManager.shared.fetchWidgetData { response, isLoggedOut in
            let date = Date()
            let entry = WidgetEntry(date: date, response: response, isLoggedOut: isLoggedOut)
            
            // Refresh widget content hourly
            let refreshDate = Calendar.current.date(byAdding: .hour, value: 1, to: date)!
            let timeline = Timeline(entries: [entry], policy: .after(refreshDate))
            completion(timeline)
        }
    }
}

// MARK: - Widget Views

struct WidgetCommonBackground: View {
    var body: some View {
        // Shared dark glassmorphic styling
        ContainerRelativeShape()
            .fill(Color(red: 15/255, green: 10/255, blue: 28/255))
            .overlay(
                ContainerRelativeShape()
                    .stroke(Color.white.opacity(0.06), lineWidth: 1)
            )
    }
}

struct WidgetLogGateView: View {
    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: "lock.shield")
                .font(.title2)
                .foregroundColor(.accentColor)
            Text("Open MindCradle")
                .font(.caption)
                .fontWeight(.medium)
            Text("Sign in to sync your reflections.")
                .font(.system(size: 9))
                .foregroundColor(.gray)
                .multilineTextAlignment(.center)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(WidgetCommonBackground())
    }
}

// MARK: 1. ARIA Widget

struct AriaWidgetEntryView: View {
    var entry: WidgetProvider.Entry
    @Environment(\.widgetFamily) var family
    
    var body: some View {
        if entry.isLoggedOut {
            WidgetLogGateView()
        } else {
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 4) {
                    Image(systemName: "sparkles")
                        .foregroundColor(.accentColor)
                        .font(.system(size: 11))
                    Text("ARIA")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundColor(.gray)
                }
                
                let msg = entry.response?.aria.message ?? "How are you feeling today?"
                Text("\"\(msg)\"")
                    .font(family == .large ? .body : .caption)
                    .fontWeight(.light)
                    .lineLimit(family == .small ? 3 : 5)
                    .minimumScaleFactor(0.8)
                    .foregroundColor(.white)
                
                Spacer()
                
                HStack {
                    Text("mindcradle://aria")
                        .font(.system(size: 8))
                        .foregroundColor(.white.opacity(0.4))
                    Spacer()
                    Link(destination: URL(string: "mindcradle://aria")!) {
                        Text("Talk")
                            .font(.system(size: 9, weight: .bold))
                            .foregroundColor(.black)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 4)
                            .background(Color.accentColor)
                            .cornerRadius(8)
                    }
                }
            }
            .padding()
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(WidgetCommonBackground())
        }
    }
}

struct AriaWidget: Widget {
    let kind: String = "AriaWidget"
    
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: WidgetProvider()) { entry in
            AriaWidgetEntryView(entry: entry)
                .accentColor(Color(red: 254/255, green: 180/255, blue: 123/255)) // CIE Gold
        }
        .configurationDisplayName("ARIA Companion")
        .description("Draw calm focus suggestions and reflections from ARIA on your screen.")
        .supportedFamilies([.systemSmall, .systemMedium, .systemLarge])
    }
}

// MARK: 2. Quick Journal Widget

struct JournalWidgetEntryView: View {
    var entry: WidgetProvider.Entry
    
    var body: some View {
        if entry.isLoggedOut {
            WidgetLogGateView()
        } else {
            VStack(alignment: .leading, spacing: 8) {
                Text("DAILY JOURNAL")
                    .font(.system(size: 8, weight: .bold))
                    .foregroundColor(.gray)
                
                let prompt = entry.response?.journal.prompt ?? "What's on your mind?"
                Text(prompt)
                    .font(.caption)
                    .foregroundColor(.white)
                    .lineLimit(3)
                
                Spacer()
                
                HStack {
                    Spacer()
                    Link(destination: URL(string: "mindcradle://journal/new")!) {
                        Text("Write")
                            .font(.system(size: 9, weight: .bold))
                            .foregroundColor(.black)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 5)
                            .background(Color.accentColor)
                            .cornerRadius(8)
                    }
                }
            }
            .padding()
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(WidgetCommonBackground())
        }
    }
}

struct JournalWidget: Widget {
    let kind: String = "JournalWidget"
    
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: WidgetProvider()) { entry in
            JournalWidgetEntryView(entry: entry)
                .accentColor(Color(red: 254/255, green: 180/255, blue: 123/255))
        }
        .configurationDisplayName("Quick Journal")
        .description("Instantly open the journal composer with a reflective daily prompt.")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}

// MARK: 3. Daily Insight Widget

struct InsightWidgetEntryView: View {
    var entry: WidgetProvider.Entry
    
    var body: some View {
        if entry.isLoggedOut {
            WidgetLogGateView()
        } else {
            VStack(alignment: .leading, spacing: 8) {
                Text("TODAY'S INSIGHT")
                    .font(.system(size: 8, weight: .bold))
                    .foregroundColor(.gray)
                
                let text = entry.response?.insight.text ?? "Keep journaling. MindCradle will begin discovering patterns as your history grows."
                Text(text)
                    .font(.caption)
                    .foregroundColor(.white)
                    .lineLimit(3)
                    .minimumScaleFactor(0.9)
                
                Spacer()
                
                HStack {
                    Text("mindcradle://insight")
                        .font(.system(size: 8))
                        .foregroundColor(.white.opacity(0.4))
                    Spacer()
                    Link(destination: URL(string: "mindcradle://insight")!) {
                        Text("Explore")
                            .font(.system(size: 9, weight: .bold))
                            .foregroundColor(.accentColor)
                    }
                }
            }
            .padding()
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(WidgetCommonBackground())
        }
    }
}

struct InsightWidget: Widget {
    let kind: String = "InsightWidget"
    
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: WidgetProvider()) { entry in
            InsightWidgetEntryView(entry: entry)
                .accentColor(Color(red: 254/255, green: 180/255, blue: 123/255))
        }
        .configurationDisplayName("Daily Insight")
        .description("Displays core correlation patterns compiled by your Memory Engine.")
        .supportedFamilies([.systemMedium])
    }
}

// MARK: 4. Memory Widget

struct MemoryWidgetEntryView: View {
    var entry: WidgetProvider.Entry
    
    var body: some View {
        if entry.isLoggedOut {
            WidgetLogGateView()
        } else {
            VStack(alignment: .leading, spacing: 8) {
                Text("FROM YOUR MEMORY")
                    .font(.system(size: 8, weight: .bold))
                    .foregroundColor(.gray)
                
                let text = entry.response?.memory.text ?? "Keep reflecting. MindCradle will preserve your meaningful moments here as your history grows."
                Text("\"\(text)\"")
                    .font(.caption)
                    .foregroundColor(.white)
                    .lineLimit(3)
                    .minimumScaleFactor(0.9)
                
                Spacer()
                
                HStack {
                    Text("mindcradle://memory")
                        .font(.system(size: 8))
                        .foregroundColor(.white.opacity(0.4))
                    Spacer()
                    Link(destination: URL(string: "mindcradle://memory")!) {
                        Text("View Memory")
                            .font(.system(size: 9, weight: .bold))
                            .foregroundColor(.accentColor)
                    }
                }
            }
            .padding()
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(WidgetCommonBackground())
        }
    }
}

struct MemoryWidget: Widget {
    let kind: String = "MemoryWidget"
    
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: WidgetProvider()) { entry in
            MemoryWidgetEntryView(entry: entry)
                .accentColor(Color(red: 254/255, green: 180/255, blue: 123/255))
        }
        .configurationDisplayName("Memory Recall")
        .description("Recall meaningful memories from your personal reflection history.")
        .supportedFamilies([.systemMedium])
    }
}

// MARK: 5. Streak Widget

struct StreakWidgetEntryView: View {
    var entry: WidgetProvider.Entry
    
    var body: some View {
        if entry.isLoggedOut {
            WidgetLogGateView()
        } else {
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 4) {
                    Image(systemName: "flame.fill")
                        .foregroundColor(.accentColor)
                        .font(.title2)
                    let count = entry.response?.streak.days ?? 0
                    Text("\(count) DAYS")
                        .font(.system(size: 18, weight: .bold))
                        .foregroundColor(.white)
                }
                
                let msg = entry.response?.streak.message ?? "Ready for another day?"
                Text(msg)
                    .font(.system(size: 9, weight: .light))
                    .foregroundColor(.white.opacity(0.8))
                    .lineLimit(2)
                
                Spacer()
                
                Text("mindcradle://home")
                    .font(.system(size: 8))
                    .foregroundColor(.white.opacity(0.4))
            }
            .padding()
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(WidgetCommonBackground())
        }
    }
}

struct StreakWidget: Widget {
    let kind: String = "StreakWidget"
    
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: WidgetProvider()) { entry in
            StreakWidgetEntryView(entry: entry)
                .accentColor(Color(red: 254/255, green: 180/255, blue: 123/255))
        }
        .configurationDisplayName("Streak Counter")
        .description("Check your active reflection streak without opening the application.")
        .supportedFamilies([.systemSmall])
    }
}

// MARK: - Widget Bundle Registration

@main
struct MindCradleWidgetsBundle: WidgetBundle {
    var body: some Widget {
        AriaWidget()
        JournalWidget()
        InsightWidget()
        MemoryWidget()
        StreakWidget()
    }
}
