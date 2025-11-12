method Inc(x:int) returns (r:int)
  ensures r == x + 1
{
  r := x + 1;
}

method SafeDiv(n:int, d:int) returns (q:int)
  requires d != 0
  ensures n == q * d + n % d  // standard division identity
{
  q := n / d;
}

// Simple loop with an invariant
method CountDown(n:nat) returns (i:int)
  ensures i == 0
{
  i := n;
  while i > 0
    invariant i >= 0
  {
    i := i - 1;
  }
}

method Demo()
{
  var a := Inc(41);
  assert a == 42;           // proves from Inc's postcondition

  var q := SafeDiv(10, 2);  // OK: precondition d != 0 holds

   var bad := SafeDiv(10, 0); 
}
