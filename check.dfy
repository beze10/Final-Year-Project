method Abs(x: int) returns (y: int)
  ensures y >= 0
  ensures y == x || y == -x
{
  if x >= 0 {
    y := x;
  } else {
    y := -x;
  }
}
