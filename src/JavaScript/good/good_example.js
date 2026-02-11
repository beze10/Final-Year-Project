// Good JavaScript

import crypto from "node:crypto";

export function renderMessage(container, message) {
  // GOOD: prevents XSS
  container.textContent = String(message);
}

export function createSessionToken() {
  // GOOD: cryptographically secure random token
  return crypto.randomBytes(32).toString("hex");
}
