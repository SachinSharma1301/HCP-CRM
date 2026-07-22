import Header from "./components/Header";
import LogInteractionForm from "./components/LogInteractionForm";
import ChatAssistant from "./components/ChatAssistant";

export default function App() {
  return (
    <div className="app-shell">
      <Header />
      <div className="log-screen">
        <LogInteractionForm />
        <ChatAssistant />
      </div>
    </div>
  );
}
