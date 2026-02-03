predicate IsNonNegative(x: int)
{
  x >= 0
}

function AbsSpec(x: int): int
{
  if x >= 0 then x else -x
}

method AbsVerified(x: int) returns (y: int)
  ensures IsNonNegative(y)
  ensures y == AbsSpec(x)
{
  if x >= 0 {
    y := x;
  } else {
    y := -x;
  }
}
