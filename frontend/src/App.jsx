import { useState } from "react";
import Login from "./Login";
import MainScreen from "./MainScreen";
import { clearUserId } from "./api";

export default function App() {
  const [userId, setUserId] = useState(localStorage.getItem("user_id"));

  if (userId) {
    return <MainScreen onLogout={() => { clearUserId(); setUserId(null); }} />;
  }
  return <Login onLogin={(id) => setUserId(id)} />;
}
