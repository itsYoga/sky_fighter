import pygame
import random
import threading
import time
import math
import DAN

# --- IoTtalk Settings ---
ServerURL = 'https://class.iottalk.tw'
Reg_addr = None  # None = 使用 MAC address

# 註冊裝置
DAN.profile = {
    'd_name': 'Sky_Fighter',
    'dm_name': 'Dummy_Device',
    'is_sim': False,  # 必須要有這個欄位，False 表示這是真實裝置
    'df_list': ['Dummy_Control'],
}

current_tilt = 0.0

# --- IoTtalk Listener ---
def iottalk_listener():
    global current_tilt
    DAN.device_registration_with_retry(ServerURL, Reg_addr)
    print("=" * 50)
    print("✅ IoTtalk 連線成功！")
    print("📱 請確認 IoTtalk 網頁上已連接：")
    print("   Smartphone (Gyroscope) -> Dummy_Device (Dummy_Control)")
    print("=" * 50)

    while True:
        try:
            data = DAN.pull('Dummy_Control')
            if data is not None:
                gamma_value = None
                
                # 處理 Gyroscope 數據格式：[[alpha, beta, gamma]]
                if isinstance(data, (list, tuple)):
                    if len(data) >= 1:
                        # 數據可能是嵌套列表：[[alpha, beta, gamma]]
                        val = data[0]
                        if isinstance(val, (list, tuple)) and len(val) >= 3:
                            # 提取 Gamma 值（索引 2，用於左右傾斜控制）
                            try:
                                gamma_value = float(val[2])
                            except (ValueError, TypeError, IndexError):
                                pass
                        elif isinstance(val, (list, tuple)) and len(val) >= 1:
                            # 如果只有一個值，可能是單一 Gamma
                            try:
                                gamma_value = float(val[0])
                            except (ValueError, TypeError):
                                pass
                        else:
                            # 直接是數值
                            try:
                                gamma_value = float(val)
                            except (ValueError, TypeError):
                                pass
                
                if gamma_value is not None:
                    # 根據測試結果（2025-11-13，延長測試版）：
                    # 中間點（基準值）: -0.8833
                    # 極右平均值: 1.5842（向右傾斜到極限）
                    # 極左平均值: 0.5333（向左傾斜到極限）
                    # Gamma 範圍: -24.5 到 22.1
                    # 
                    # 控制邏輯：
                    # offset = gamma_value - baseline
                    # offset > 0 → 向右移動
                    # offset < 0 → 向左移動
                    
                    # 基準值（水平時的平均值）
                    baseline = -0.88
                    
                    # 計算偏移
                    offset = gamma_value - baseline
                    
                    # 設置死區（dead zone）來過濾小幅震動
                    dead_zone = 1.3  # 根據測試建議設定
                    
                    if abs(offset) < dead_zone:
                        current_tilt = 0.0
                    else:
                        # 縮放因子：將偏移值映射到 -10 到 10 的範圍
                        # 根據測試建議：scale_factor = 0.7702
                        scale_factor = 0.77  # 約 0.77
                        current_tilt = offset * scale_factor
                        # 限制在 -10 到 10 之間
                        current_tilt = max(-10, min(10, current_tilt))
                else:
                    current_tilt = 0.0
            time.sleep(0.02)  # 50Hz 更新率
        except Exception as e:
            print(f"⚠️ 連線錯誤: {e}")
            time.sleep(1)

# --- Game Constants & Colors ---
WIDTH, HEIGHT = 800, 600
FPS = 60

# Neon Palette
C_BG = (10, 10, 20)
C_NEON_CYAN = (0, 255, 255)
C_NEON_PINK = (255, 0, 255)
C_NEON_GREEN = (57, 255, 20)
C_NEON_YELLOW = (255, 240, 31)
C_WHITE = (255, 255, 255)
C_HUD_BG = (0, 0, 0, 180)

# --- Visual Effects Classes ---

class Particle(pygame.sprite.Sprite):
    def __init__(self, x, y, color, speed_x, speed_y, life):
        super().__init__()
        self.original_life = life
        self.life = life
        self.image = pygame.Surface((4, 4), pygame.SRCALPHA)
        self.image.fill(color)
        self.rect = self.image.get_rect(center=(x, y))
        self.vx = speed_x
        self.vy = speed_y
        self.color = color

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.life -= 1
        if self.life <= 0:
            self.kill()
        else:
            # Fade out effect
            alpha = int((self.life / self.original_life) * 255)
            self.image.set_alpha(alpha)

class Star:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.speed = random.uniform(0.5, 3.0)  # Parallax speed
        self.size = int(self.speed)
        self.color = random.choice([C_WHITE, C_NEON_CYAN, (100, 100, 255)])

    def update(self):
        self.y += self.speed
        if self.y > HEIGHT:
            self.y = 0
            self.x = random.randint(0, WIDTH)

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size)

# --- Game Object Classes ---

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.width = 50
        self.height = 60
        self.image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(WIDTH // 2, HEIGHT - 80))
        self.speed = 7
        self.bank_angle = 0  # For visual rotation
        
    def draw_ship(self, angle):
        # Clear surface
        self.image.fill((0, 0, 0, 0))
        
        # Create a temporary surface for rotation
        temp_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Draw Neon Ship (Triangle based)
        points = [(25, 0), (50, 60), (25, 45), (0, 60)]
        pygame.draw.polygon(temp_surf, C_NEON_CYAN, points, 2)  # Outline
        pygame.draw.polygon(temp_surf, (0, 100, 100), points)  # Fill
        
        # Engine glow
        pygame.draw.circle(temp_surf, C_NEON_PINK, (25, 50), 5)
        
        # Rotate
        rotated_image = pygame.transform.rotate(temp_surf, -angle * 2)  # Multiply for effect
        new_rect = rotated_image.get_rect(center=self.rect.center)
        
        return rotated_image, new_rect

    def update(self):
        threshold = 0.3
        tilt_magnitude = abs(current_tilt)
        
        # Movement Logic
        if tilt_magnitude > threshold:
            normalized_tilt = min((tilt_magnitude - threshold) / (8 - threshold), 1.0)
            move_speed = normalized_tilt * self.speed
            
            if current_tilt < 0:
                self.rect.x -= move_speed
                self.bank_angle = max(self.bank_angle - 2, -25)  # Bank left
            elif current_tilt > 0:
                self.rect.x += move_speed
                self.bank_angle = min(self.bank_angle + 2, 25)  # Bank right
        else:
            # Return to center tilt
            if self.bank_angle > 0:
                self.bank_angle -= 2
            elif self.bank_angle < 0:
                self.bank_angle += 2

        # Boundaries
        self.rect.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))
        
        # Update visual
        self.image, rect = self.draw_ship(self.bank_angle)
        self.rect.size = rect.size  # Update hit box size roughly

class Enemy(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.size = random.randint(30, 45)
        self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.reset_pos()
        self.rotation = 0
        self.rot_speed = random.choice([-3, 3])
        self.color = random.choice([C_NEON_PINK, C_NEON_YELLOW])

    def reset_pos(self):
        self.rect.x = random.randrange(WIDTH - self.rect.width)
        self.rect.y = random.randrange(-150, -50)
        self.speedy = random.randrange(3, 7)

    def update(self):
        self.rect.y += self.speedy
        self.rotation = (self.rotation + self.rot_speed) % 360
        
        # Draw rotating enemy
        self.image.fill((0, 0, 0, 0))
        center = self.size // 2
        
        # Abstract Hexagon/Shape
        radius = self.size // 2 - 2
        points = []
        for i in range(6):
            ang_rad = math.radians(self.rotation + i * 60)
            px = center + radius * math.cos(ang_rad)
            py = center + radius * math.sin(ang_rad)
            points.append((px, py))
            
        pygame.draw.polygon(self.image, self.color, points, 2)
        pygame.draw.circle(self.image, C_WHITE, (center, center), 4)

        if self.rect.top > HEIGHT + 10:
            self.reset_pos()

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((6, 20), pygame.SRCALPHA)
        pygame.draw.rect(self.image, C_NEON_GREEN, (0, 0, 6, 20), border_radius=3)
        pygame.draw.rect(self.image, C_WHITE, (2, 2, 2, 16), border_radius=1)  # Core
        self.rect = self.image.get_rect()
        self.rect.bottom = y
        self.rect.centerx = x
        self.speedy = -12

    def update(self):
        self.rect.y += self.speedy
        if self.rect.bottom < 0:
            self.kill()

# --- Helper Functions ---

def draw_neon_text(screen, text, font, color, center_pos, glow=True):
    text_surf = font.render(text, True, color)
    text_rect = text_surf.get_rect(center=center_pos)
    
    if glow:
        glow_surf = font.render(text, True, (color[0]//2, color[1]//2, color[2]//2))
        screen.blit(glow_surf, (text_rect.x + 2, text_rect.y + 2))
        
    screen.blit(text_surf, text_rect)
    return text_rect

def draw_hud(screen, score, elapsed_time, tilt, font):
    # Bottom Dashboard Background
    dashboard_h = 80
    s = pygame.Surface((WIDTH, dashboard_h), pygame.SRCALPHA)
    s.fill((0, 10, 20, 230))  # Semi-transparent dark blue
    pygame.draw.line(s, C_NEON_CYAN, (0, 0), (WIDTH, 0), 2)
    screen.blit(s, (0, HEIGHT - dashboard_h))
    
    center_y = HEIGHT - dashboard_h // 2
    
    # 1. Score (Left)
    draw_neon_text(screen, f"SCORE", font, C_NEON_CYAN, (100, center_y - 15), False)
    draw_neon_text(screen, f"{score:05d}", font, C_WHITE, (100, center_y + 10), True)
    
    # 2. Tilt Gauge (Center)
    gauge_w = 300
    gauge_h = 10
    gauge_x = WIDTH // 2 - gauge_w // 2
    gauge_y = center_y + 15
    
    # Gauge Background
    pygame.draw.rect(screen, (50, 50, 50), (gauge_x, gauge_y, gauge_w, gauge_h), border_radius=5)
    # Center Marker
    pygame.draw.line(screen, C_WHITE, (WIDTH//2, gauge_y-5), (WIDTH//2, gauge_y+15), 2)
    
    # Active Bar
    tilt_clamped = max(-10, min(10, tilt))
    fill_pct = tilt_clamped / 10  # -1 to 1
    bar_len = (abs(fill_pct) * (gauge_w // 2))
    
    color = C_NEON_GREEN if abs(tilt) < 3 else C_NEON_PINK
    
    if fill_pct > 0:  # Right
        pygame.draw.rect(screen, color, (WIDTH//2, gauge_y, bar_len, gauge_h), border_radius=2)
    else:  # Left
        pygame.draw.rect(screen, color, (WIDTH//2 - bar_len, gauge_y, bar_len, gauge_h), border_radius=2)
        
    # Tilt Label
    draw_neon_text(screen, "GYRO STABILIZER", pygame.font.Font(None, 20), C_NEON_CYAN, (WIDTH//2, center_y - 10), False)
    
    # 3. Time (Right)
    minutes = elapsed_time // 60
    seconds = elapsed_time % 60
    draw_neon_text(screen, f"TIME", font, C_NEON_CYAN, (WIDTH - 100, center_y - 15), False)
    draw_neon_text(screen, f"{minutes:02d}:{seconds:02d}", font, C_WHITE, (WIDTH - 100, center_y + 10), True)

# --- Main Menu ---
def main_menu(screen, clock, iottalk_connected):
    font_title = pygame.font.Font(None, 100)
    font_sub = pygame.font.Font(None, 40)
    stars = [Star() for _ in range(40)]
    
    # 預覽飛機位置
    preview_x = WIDTH // 2
    preview_y = HEIGHT - 100
    
    while True:
        screen.fill(C_BG)
        
        # Update Background
        for star in stars:
            star.update()
            star.draw(screen)
        
        # 更新預覽飛機位置（響應傾斜控制）
        threshold = 0.3
        tilt_magnitude = abs(current_tilt)
        if tilt_magnitude > threshold:
            normalized_tilt = min((tilt_magnitude - threshold) / (8 - threshold), 1.0)
            move_speed = normalized_tilt * 6
            
            if current_tilt < 0:
                preview_x -= move_speed
            elif current_tilt > 0:
                preview_x += move_speed
        
        preview_x = max(30, min(WIDTH - 30, preview_x))
        
        # Title Animation
        scale = 1.0 + 0.05 * math.sin(time.time() * 3)
        title_surf = font_title.render("SKY FIGHTER", True, C_NEON_CYAN)
        # Glow effect
        glow_surf = pygame.transform.smoothscale(title_surf, (int(title_surf.get_width()*scale), int(title_surf.get_height()*scale)))
        rect = glow_surf.get_rect(center=(WIDTH//2, HEIGHT//3))
        screen.blit(glow_surf, rect)
        
        # Connection Status
        status_col = C_NEON_GREEN if iottalk_connected else C_NEON_PINK
        status_txt = "SYSTEM ONLINE" if iottalk_connected else "WAITING FOR LINK..."
        draw_neon_text(screen, status_txt, font_sub, status_col, (WIDTH//2, HEIGHT//2))
        
        # Instruction
        if int(time.time() * 2) % 2 == 0:  # Blink
            draw_neon_text(screen, "PRESS SPACE TO LAUNCH", font_sub, C_WHITE, (WIDTH//2, HEIGHT*0.7))
        
        # Interactive Tilt Preview
        pygame.draw.rect(screen, (30, 30, 50), (WIDTH//2-100, HEIGHT-60, 200, 10))
        marker_x = WIDTH//2 + (current_tilt * 10)
        pygame.draw.circle(screen, C_NEON_YELLOW, (int(marker_x), HEIGHT-55), 8)
        
        # 繪製預覽飛機
        preview_player = Player()
        preview_player.rect.centerx = preview_x
        preview_player.rect.centery = preview_y
        preview_image, preview_rect = preview_player.draw_ship(0)
        screen.blit(preview_image, preview_rect)
        
        # 預覽說明文字
        preview_hint = pygame.font.Font(None, 22).render("Try tilting your phone to control the plane!", True, C_NEON_CYAN)
        preview_hint_rect = preview_hint.get_rect(center=(WIDTH // 2, preview_y + 40))
        screen.blit(preview_hint, preview_hint_rect)
            
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                return True
            
        pygame.display.flip()
        clock.tick(FPS)

# --- Main Loop ---
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("🎮 Sky Fighter: IoT Edition")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)

    # Start IoT Thread
    t = threading.Thread(target=iottalk_listener)
    t.daemon = True
    t.start()
    
    # Wait briefly for connection
    time.sleep(1)
    
    if not main_menu(screen, clock, True):
        pygame.quit()
        return

    # Game Setup
    all_sprites = pygame.sprite.Group()
    mobs = pygame.sprite.Group()
    bullets = pygame.sprite.Group()
    particles = pygame.sprite.Group()
    
    player = Player()
    all_sprites.add(player)
    
    # Create Stars
    star_bg = [Star() for _ in range(50)]

    for i in range(6):
        m = Enemy()
        all_sprites.add(m)
        mobs.add(m)

    score = 0
    start_time = time.time()
    last_shot = 0
    running = True

    while running:
        dt = clock.tick(FPS)
        now = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Auto Shoot
        if now - last_shot > 0.2:
            b = Bullet(player.rect.centerx, player.rect.top)
            all_sprites.add(b)
            bullets.add(b)
            last_shot = now

        # Updates
        # Player Engine Particles
        if random.random() < 0.5:
            p = Particle(player.rect.centerx, player.rect.bottom - 5, C_NEON_CYAN, 
                        random.uniform(-1, 1), random.uniform(2, 5), 20)
            all_sprites.add(p)
            particles.add(p)

        for star in star_bg:
            star.update()
        all_sprites.update()

        # Collisions: Bullet hits Mob
        hits = pygame.sprite.groupcollide(mobs, bullets, True, True)
        for hit in hits:
            score += 100
            # Explosion Particles
            for _ in range(15):
                p = Particle(hit.rect.centerx, hit.rect.centery, hit.color, 
                            random.uniform(-5, 5), random.uniform(-5, 5), 30)
                all_sprites.add(p)
                particles.add(p)
                
            m = Enemy()
            all_sprites.add(m)
            mobs.add(m)

        # Collisions: Mob hits Player
        if pygame.sprite.spritecollide(player, mobs, False):
            running = False  # Simple Game Over

        # --- Draw ---
        screen.fill(C_BG)
        
        # Draw Stars
        for star in star_bg:
            star.draw(screen)
        
        # Draw Sprites
        all_sprites.draw(screen)
        
        # Draw HUD
        elapsed = int(now - start_time)
        draw_hud(screen, score, elapsed, current_tilt, font)

        pygame.display.flip()

    # Game Over Screen
    time.sleep(0.5)
    screen.fill((0, 0, 0))
    draw_neon_text(screen, "MISSION FAILED", pygame.font.Font(None, 80), C_NEON_PINK, (WIDTH//2, HEIGHT//2 - 50))
    draw_neon_text(screen, f"FINAL SCORE: {score}", font, C_WHITE, (WIDTH//2, HEIGHT//2 + 20))
    pygame.display.flip()
    time.sleep(3)
    pygame.quit()

if __name__ == '__main__':
    main()
