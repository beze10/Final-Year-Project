// check.dfy
// A small "real" verification check: we call a helper method that requires a non-negative input,
// and we prove that requirement is satisfied before calling it.

method IncNonNeg(x: int) returns (y: int)
  requires x >= 0
  ensures y == x + 1
  ensures y >= 1
{
  y := x + 1;
}

method Check(a: int) returns (b: int)
  requires a >= 0
  ensures b == a + 2
  ensures b >= 2
{
  // First call is safe because a >= 0 (from the requires clause)
  var t := IncNonNeg(a);

  // Second call is also safe because t >= 1 (from IncNonNeg's postcondition),
  // and 1 >= 0 implies t >= 0.
  var u := IncNonNeg(t);

  b := u;
}
