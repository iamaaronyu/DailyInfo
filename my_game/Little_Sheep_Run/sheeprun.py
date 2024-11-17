import pygame
import os
import random
import sys
from tkinter import messagebox, Tk

# 初始化 pygame
pygame.init()

# 设置资源目录的根路径
ASSETS_DIR = "assets"
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")

# 屏幕设置
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 400
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("小羊快跑")

# 加载图片
background_image = pygame.image.load(os.path.join(IMAGES_DIR, "caodi.png"))
player_image = pygame.image.load(os.path.join(IMAGES_DIR, "yang.png"))
obstacle_image = pygame.image.load(os.path.join(IMAGES_DIR, "lang.png"))

# 缩放角色和障碍物图片
player_image = pygame.transform.scale(player_image, (50, 50))
obstacle_image = pygame.transform.scale(obstacle_image, (50, 50))

# 加载音乐和音效
pygame.mixer.init()
pygame.mixer.music.load(os.path.join(SOUNDS_DIR, "background_music.mp3"))
pygame.mixer.music.set_volume(0.5)
pygame.mixer.music.play(-1)  # 循环播放

collision_sound = pygame.mixer.Sound(os.path.join(SOUNDS_DIR, "collision_sound.mp3"))
collision_sound.set_volume(0.7)

# 加载字体
font = pygame.font.Font(os.path.join(FONTS_DIR, "simhei.ttf"), 28)

# 游戏时钟
clock = pygame.time.Clock()

# 角色类
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = player_image
        self.rect = self.image.get_rect()
        self.rect.center = (100, SCREEN_HEIGHT - 75)
        self.base_speed = 5  # 基础速度

    def calculate_speed(self, score):
        """根据当前得分动态调整速度"""
        return self.base_speed + score // 200  # 每200分速度增加1

    def update(self, score):
        # 获取当前速度
        current_speed = self.calculate_speed(score)

        # 处理键盘输入
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and self.rect.left > 0:
            self.rect.x -= current_speed
        if keys[pygame.K_RIGHT] and self.rect.right < SCREEN_WIDTH:
            self.rect.x += current_speed
        if keys[pygame.K_UP] and self.rect.top > 0:
            self.rect.y -= current_speed
        if keys[pygame.K_DOWN] and self.rect.bottom < SCREEN_HEIGHT:
            self.rect.y += current_speed

class Obstacle(pygame.sprite.Sprite):
    def __init__(self, player_x, player_y, score):
        super().__init__()
        self.image = obstacle_image
        self.rect = self.image.get_rect()

        # 障碍物生成在屏幕右侧
        self.rect.x = random.randint(SCREEN_WIDTH, SCREEN_WIDTH + 200)

        # 障碍物的垂直位置基于玩家上下随机分布
        vertical_offset = random.randint(-100, 100)  # 上下100像素范围内
        self.rect.y = max(0, min(SCREEN_HEIGHT - self.rect.height, player_y + vertical_offset))

        self.speed = self.calculate_speed(score)  # 根据得分动态调整速度

    def calculate_speed(self, score):
        """根据当前得分计算障碍物速度"""
        base_speed = 3
        return base_speed + score // 100  # 每100分速度增加1

    def update(self):
        self.rect.x -= self.speed
        if self.rect.right < 0:
            self.kill()  # 移出屏幕后销毁


def initialize_game(score=0):
    player = Player()
    player_group = pygame.sprite.Group(player)

    # 初始障碍物数量为5
    obstacle_group = pygame.sprite.Group()
    for _ in range(5):
        new_obstacle = Obstacle(player.rect.x, player.rect.y, score)  # 传递当前分数和玩家位置
        obstacle_group.add(new_obstacle)

    return player_group, obstacle_group


# 绘制背景平铺函数
def draw_tiled_background(screen, background_image):
    bg_width, bg_height = background_image.get_size()
    for x in range(0, SCREEN_WIDTH, bg_width):
        for y in range(0, SCREEN_HEIGHT, bg_height):
            screen.blit(background_image, (x, y))

def main():
    player_group, obstacle_group = initialize_game()
    score = 0
    high_score = 0  # 初始化最高分
    # font = pygame.font.Font("simhei.ttf", 28)

    last_obstacle_time = 0  # 上次生成障碍物的时间

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # 更新角色和障碍物
        # player_group.update()
        player_group.update(score)
        obstacle_group.update()

        # 获取当前时间
        current_time = pygame.time.get_ticks()

        # 每100毫秒生成一批障碍物
        if current_time - last_obstacle_time > 800:
            last_obstacle_time = current_time
            player = player_group.sprites()[0]

            # 根据分数生成障碍物
            obstacle_count = 1 + score // 500
            for _ in range(obstacle_count):
                new_obstacle = Obstacle(player.rect.x, player.rect.y, score)
                obstacle_group.add(new_obstacle)

        # 碰撞检测
        if pygame.sprite.spritecollideany(player_group.sprites()[0], obstacle_group):
            pygame.mixer.music.stop()
            collision_sound.play()

            # 更新最高分
            if score > high_score:
                high_score = score

            root = Tk()
            root.withdraw()
            result = messagebox.askyesno("游戏结束", "再来一次？")
            root.destroy()

            if result:
                pygame.mixer.music.play(-1)
                player_group, obstacle_group = initialize_game(score=0)
                score = 0
            else:
                pygame.quit()
                sys.exit()

        # 绘制背景
        draw_tiled_background(screen, background_image)

        # 绘制角色和障碍物
        player_group.draw(screen)
        obstacle_group.draw(screen)

        # 显示得分
        score += 1
        score_text = font.render(f"得分: {score}", True, (0, 0, 0))
        screen.blit(score_text, (10, 10))

        # 显示最高分
        high_score_text = font.render(f"最高分: {high_score}", True, (0, 0, 0))
        screen.blit(high_score_text, (10, 50))

        # 刷新屏幕
        pygame.display.flip()
        clock.tick(30)


if __name__ == "__main__":
    main()
