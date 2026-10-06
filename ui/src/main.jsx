import { createRoot } from "react-dom/client";
import App from "./App";
import { connect } from "./store";
import { startStory } from "./story";
import "./styles.css";

connect();
startStory();
createRoot(document.getElementById("root")).render(<App />);
