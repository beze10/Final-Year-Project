import { exec } from "node:child_process";

export function renderMessageUnsafe(container, message) {
  // BAD: DOM-based XSS
  container.innerHTML = message;
}

export function runCommand(userInput) {
  // BAD: command injection
  exec("ls " + userInput);
}

export function insecureToken() {
  // BAD: weak randomness
  return Math.random().toString(36);
}
