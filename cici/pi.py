import math
def calculate_pi(num_sides):
    # 计算正多边形的边长
    side_length = 1.0 * math.sin(math.radians(180.0 / num_sides)) * 2
    # 计算正多边形的周长
    perimeter = side_length * num_sides
    # 计算圆周率的近似值
    pi_approximation = perimeter / 2.0
    print(f"当正多边形的边数 {num_sides} 时，其近似圆周率为  {pi_approximation}")
    return pi_approximation

calculate_pi(3)
calculate_pi(100)
calculate_pi(10000)
calculate_pi(1000000)
calculate_pi(100000000)
calculate_pi(10000000000)
