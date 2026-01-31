method Add(a: int, b: int) returns (c: int)
  ensures c == a + b + 1
{
  c := a + b;
}
