import { useState } from “react”;
import “./App.css”;

const API_URL = “http://127.0.0.1:8000”;

  function App() {
    const [command, setCommand] = useState(””);
    const [response, setResponse] = useState(””);
    const [status, setStatus] = useState(“Ready”);
    const [loading, setLoading] = useState(false);

    async function sendCommand(event) {
      event.preventDefault();

      if (!command.trim()) return;
      setLoading(true);
      setResponse("");
      setStatus("Understanding your request...");
      try {
        const result = await fetch(`${API_URL}/api/command`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            command,
            language: "hi-IN",
          }),
        });
        if (!result.ok) {
          throw new Error("Backend request failed");
        }
        const data = await result.json();
        setResponse(data.message);
        setStatus(`Intent: ${data.intent} | Status: ${data.status}`);
      } catch {
        setResponse(
          "Backend se connection nahi ho paaya. Please check the server."
        );
        setStatus("Connection error");
      } finally {
        setLoading(false);
      }

    }

    function speakResponse() {
      if (!response || !(“speechSynthesis” in window)) return;

      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(response);
      utterance.lang = "hi-IN";
      window.speechSynthesis.speak(utterance);

    }

    return (
      A
AwaazWeb
Speak naturally.Browse independently.
  < section className = "hero" >
    <span className="badge">VOICE-FIRST WEB ASSISTANT</span>
    <h2>Your voice. Your control.</h2>
    <p className="description">
      Websites navigate karna ab aur aasaan.
      Bataiye, aapko kya karna hai?
    </p>
    <form onSubmit={sendCommand}>
      <label htmlFor="command">Your command</label>
      <textarea
        id="command"
        value={command}
        onChange={(event) => setCommand(event.target.value)}
        placeholder="Mere scholarship application ka status batao..."
        rows={3}
      />
      <button type="submit" disabled={loading}>
        {loading ? "Processing..." : "Ask AwaazWeb"}
      </button>
    </form>
    <div className="status" role="status" aria-live="polite">
      {status}
    </div>
    {
      response && (
        <section className="response" aria-labelledby="response-title">
          <h3 id="response-title">AwaazWeb says</h3>
          <p>{response}</p>
          <button
            type="button"
            className="secondary"
            onClick={speakResponse}
          >
            Speak response
          </button>
        </section>
      )
    }
  </section >
      <footer>
        AwaazWeb · Accessible technology, designed for independence.
      </footer>
</main >

);
  }

export default App;