// specs/python_js_security_policy.dfy
// Dafny POLICY spec for your Python/JS good vs bad examples.
// - Semgrep checks the actual Python/JS code patterns.
// - Dafny proves the underlying security policies are logically sound.

module PythonJsSecurityPolicy {

  // -----------------------------
  // Helpers
  // -----------------------------

  predicate IsAlphaNumUnderscore(c: char)
  {
    ('a' <= c <= 'z') ||
    ('A' <= c <= 'Z') ||
    ('0' <= c <= '9') ||
    c == '_'
  }

  predicate ValidUsername(u: seq<char>)
  {
    3 <= |u| <= 20 &&
    (forall i :: 0 <= i < |u| ==> IsAlphaNumUnderscore(u[i]))
  }

  predicate Contains(hay: seq<char>, needle: seq<char>)
  {
    |needle| == 0 ||
    (|needle| <= |hay| &&
      exists i {:trigger hay[i .. i + |needle|]} :: 0 <= i <= |hay| - |needle| &&
        hay[i .. i + |needle|] == needle)
  }

  // -----------------------------
  // 1. Python: safe query policy
  // -----------------------------
  // Python good_example.py: parameterised query
  // Python bad_example.py: string concatenation embeds user input into SQL text

  datatype SqlQuery =
    | ParamQuery(template: seq<char>, params: seq<seq<char>>)
    | RawQuery(text: seq<char>)

  // Core policy:
  // User input must NOT be embedded directly inside SQL text.
  // (It may be passed as a separate parameter.)
  predicate SafeSql(q: SqlQuery, userInput: seq<char>)
  {
    match q
      // Parameterised queries are safe because user input is passed separately
      case ParamQuery(t, ps) => true
      case RawQuery(t)       => !Contains(t, userInput)
  }

  // A "good" builder: equivalent to
  // cursor.execute("... username = ?", (username,))
  method BuildUserLookupQuery_Good(username: seq<char>) returns (q: SqlQuery)
    requires ValidUsername(username)
    ensures SafeSql(q, username)
  {
    q := ParamQuery("SELECT id, username FROM users WHERE username = ?", [username]);
  }

  // A "bad" builder: equivalent to
  // "SELECT ... '" + username + "'"
  method BuildUserLookupQuery_Bad(username: seq<char>) returns (q: SqlQuery)
    ensures !SafeSql(q, username)
  {
    var prefix := "SELECT * FROM users WHERE username = '";
    var suffix := "'";
    var t := prefix + username + suffix;
    q := RawQuery(t);
    if |username| == 0 {
      // empty needle is considered contained by definition
      assert Contains(t, username);
    } else {
      var i := |prefix|;
      assert 0 <= i <= |t| - |username|;
      assert t[i .. i + |username|] == username;
      assert Contains(t, username);
    }
  }

  // -----------------------------
  // 2. Python/JS: no eval policy
  // -----------------------------
  // Python bad_example.py uses eval(user_input)
  // JS bad_example.js uses eval(userInput)
  //
  // Policy: evaluating untrusted user strings as code is forbidden.
  predicate AllowEvalOnUserInput() { false }

  method EvalUserInput(userInput: seq<char>) returns (r: int)
    requires AllowEvalOnUserInput() // impossible by policy
  {
    r := 0;
  }

  // -----------------------------
  // 3. JS: safe rendering policy (XSS)
  // -----------------------------
  // JS good_example.js uses textContent (TextOnly)
  // JS bad_example.js uses innerHTML (Html)

  datatype RenderMode = TextOnly | Html

  predicate SafeRender(mode: RenderMode)
  {
    mode == TextOnly
  }

  method Render_Good(userInput: seq<char>) returns (mode: RenderMode)
    ensures SafeRender(mode)
  {
    mode := TextOnly;
  }

  method Render_Bad(userInput: seq<char>) returns (mode: RenderMode)
    ensures !SafeRender(mode)
  {
    mode := Html;
  }

  // -----------------------------
  // 4. JS: secure token generation policy
  // -----------------------------
  // JS good_example.js uses crypto.randomBytes (ApprovedCSPRNG)
  // JS bad_example.js uses Math.random (NonCryptoPRNG)

  datatype TokenSource = ApprovedCSPRNG | NonCryptoPRNG

  predicate SecureTokenSource(src: TokenSource)
  {
    src == ApprovedCSPRNG
  }

  method CreateToken_Good() returns (src: TokenSource)
    ensures SecureTokenSource(src)
  {
    src := ApprovedCSPRNG;
  }

  method CreateToken_Bad() returns (src: TokenSource)
    ensures !SecureTokenSource(src)
  {
    src := NonCryptoPRNG;
  }

  // -----------------------------
  // 5. JS: command execution policy (command injection)
  // -----------------------------
  // JS bad_example.js: exec("ls " + userInput)
  //
  // Policy: never construct shell commands by concatenating user input.

  datatype Command =
    | Argv(program: seq<char>, args: seq<seq<char>>)  // safer interface
    | Shell(text: seq<char>)                          // risky interface

  predicate SafeCommand(cmd: Command, userInput: seq<char>)
  {
    match cmd
      case Argv(p, args) => true
      case Shell(t)      => !Contains(t, userInput)
  }

  method BuildCommand_Good(userArg: seq<char>) returns (cmd: Command)
    ensures SafeCommand(cmd, userArg)
  {
    // Models: execFile("ls", ["-la", userArg])
    cmd := Argv("ls", ["-la", userArg]);
  }

  method BuildCommand_Bad(userArg: seq<char>) returns (cmd: Command)
    ensures !SafeCommand(cmd, userArg)
  {
    var prefix := "ls ";
    var t := prefix + userArg;
    // Models: exec("ls " + userArg)
    cmd := Shell(t);
    if |userArg| == 0 {
      assert Contains(t, userArg);
    } else {
      var i := |prefix|;
      assert 0 <= i <= |t| - |userArg|;
      assert t[i .. i + |userArg|] == userArg;
      assert Contains(t, userArg);
    }
  }

  // -----------------------------
  // 6. Small sanity lemmas (optional but nice for reports)
  // -----------------------------

  lemma UsernamePolicyHasWitness()
    ensures exists u: seq<char> :: ValidUsername(u)
  {
    var u := "abc";
    assert ValidUsername(u);
  }

  lemma UsernamePolicyRejectsTooShort()
    ensures !ValidUsername("ab")
  { }

  lemma SafeRenderRejectsHtml()
    ensures !SafeRender(Html)
  { }

  lemma SecureTokenRejectsNonCrypto()
    ensures !SecureTokenSource(NonCryptoPRNG)
  { }
}
