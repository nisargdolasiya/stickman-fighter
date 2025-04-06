import pygame
import sys
import math
import random  # For enemy AI randomization

# Initialize Pygame
pygame.init()

# Set up the display
WIDTH = 800
HEIGHT = 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Stickman Fight")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 100, 255)
GRAY = (128, 128, 128)
SILVER = (192, 192, 192)

# Particle system
class Particle:
    def __init__(self, x, y, color, size=2, speed=2, lifetime=30):
        self.x = x
        self.y = y
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        # Random direction
        angle = random.uniform(0, math.pi * 2)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 1  # Slight upward bias
        
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.1  # Gravity
        self.lifetime -= 1
        return self.lifetime > 0
        
    def draw(self, surface):
        alpha = int(255 * (self.lifetime / self.max_lifetime))
        s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (self.size, self.size), self.size)
        surface.blit(s, (int(self.x - self.size), int(self.y - self.size)))


# Slash effect class
class SlashEffect:
    def __init__(self, x, y, angle, size, color):
        self.x = x
        self.y = y
        self.angle = angle
        self.size = size
        self.base_color = color
        self.alpha = 255
        self.fade_speed = 25
        self.lines = self.generate_lines()

    def generate_lines(self):
        lines = []
        # Generate just 2 parallel lines for a cleaner look
        main_angle = math.radians(self.angle)
        perp_angle = main_angle + math.pi/2
        gap = 5  # Gap between parallel lines
        
        for offset in [-gap/2, gap/2]:
            start_x = self.x + math.cos(perp_angle) * offset
            start_y = self.y + math.sin(perp_angle) * offset
            end_x = start_x + math.cos(main_angle) * self.size
            end_y = start_y + math.sin(main_angle) * self.size
            lines.append(((start_x, start_y), (end_x, end_y)))
        return lines

    def update(self):
        self.alpha -= self.fade_speed
        return self.alpha > 0

    def draw(self, surface):
        # Create a surface for the slash with alpha channel
        slash_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        
        for start, end in self.lines:
            # Main line
            color = (*self.base_color, self.alpha)
            pygame.draw.line(slash_surface, color, start, end, 2)
            
            # Subtle glow
            glow_color = (*self.base_color, self.alpha // 3)
            pygame.draw.line(slash_surface, glow_color, start, end, 4)
        
        surface.blit(slash_surface, (0, 0))

# Ground position
GROUND_Y = HEIGHT - 50

class Stickman:
    def __init__(self, x, facing_right=True):
        self.x = x
        self.y = GROUND_Y
        self.size = 50
        self.speed = 5
        self.facing_right = facing_right
        self.attacking = False
        self.attack_frame = 0
        self.health = 100
        self.weapon_angle = 0
        self.hit_cooldown = 0
        self.dead = False
        self.combo_count = 0
        self.combo_timer = 0
        self.max_combo = 3
        self.slash_effects = []
        self.particles = []  # For smoke effects
        # New movement mechanics
        self.vel_y = 0
        self.is_jumping = False
        self.jump_power = -15
        self.gravity = 0.8
        self.dash_speed = 15
        self.dash_duration = 10
        self.dash_cooldown = 0
        self.dash_cooldown_max = 30
        self.is_dashing = False
        self.dash_direction = 1
        self.dash_trail = []
        # Aerial attack
        self.spinning = False
        self.spin_angle = 0

    def draw(self, surface):
        # Draw dash trail
        for trail in self.dash_trail:
            alpha = min(trail['alpha'], 255)
            trail_color = (100, 200, 255, alpha)
            trail_surface = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(trail_surface, trail_color, (5, 5), 5)
            surface.blit(trail_surface, (trail['x'] - 5, trail['y'] - 5))
            
        # Flash white when hit (invulnerability frames)
        draw_color = (255, 255, 255, 128) if self.hit_cooldown > 0 else BLACK
        
        # Draw particles
        for particle in self.particles:
            particle.draw(surface)
        
        # Draw slash effects
        for effect in self.slash_effects:
            effect.draw(surface)
            
        if self.dead:
            self.draw_dead(surface)
            return

        if self.spinning:
            # Calculate rotated points for spinning animation
            angle = math.radians(self.spin_angle)
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            
            # Rotate points around center
            def rotate_point(x, y):
                rx = (x - self.x) * cos_a - (y - (self.y - self.size//2)) * sin_a + self.x
                ry = (x - self.x) * sin_a + (y - (self.y - self.size//2)) * cos_a + (self.y - self.size//2)
                return (rx, ry)
            
            # Draw rotated stickman
            # Head
            head_pos = rotate_point(self.x, self.y - self.size)
            pygame.draw.circle(surface, BLACK, head_pos, self.size // 4, 2)
            
            # Body
            body_start = rotate_point(self.x, self.y - self.size + self.size//4)
            body_end = rotate_point(self.x, self.y - self.size//2)
            pygame.draw.line(surface, draw_color, body_start, body_end, 2)
            
            # Legs
            leg1_end = rotate_point(self.x - self.size//4, self.y)
            leg2_end = rotate_point(self.x + self.size//4, self.y)
            pygame.draw.line(surface, draw_color, body_end, leg1_end, 2)
            pygame.draw.line(surface, draw_color, body_end, leg2_end, 2)
            
            # Arms and spinning sword
            arm_pos = rotate_point(self.x, self.y - self.size + self.size//3)
            weapon_length = self.size * 1.5  # Longer sword for spin attack
            weapon_angle = angle + (math.pi/4 if self.facing_right else -math.pi/4)
            weapon_end = (
                arm_pos[0] + math.cos(weapon_angle) * weapon_length,
                arm_pos[1] + math.sin(weapon_angle) * weapon_length
            )
            
            # Draw the spinning sword
            pygame.draw.line(surface, draw_color, arm_pos, weapon_end, 3)
            
        else:
            # Normal stickman drawing
            # Draw head
            pygame.draw.circle(surface, BLACK, (self.x, self.y - self.size), self.size // 4, 2)

            # Draw body
            pygame.draw.line(surface, BLACK, (self.x, self.y - self.size + self.size//4),
                            (self.x, self.y - self.size//2), 2)

            # Draw legs with running animation if moving
            leg_offset = math.sin(pygame.time.get_ticks() * 0.01) * 10 if abs(self.speed) > 0 else 0
            pygame.draw.line(surface, BLACK, (self.x, self.y - self.size//2),
                            (self.x - self.size//4 + leg_offset, self.y), 2)
            pygame.draw.line(surface, BLACK, (self.x, self.y - self.size//2),
                            (self.x + self.size//4 - leg_offset, self.y), 2)

            # Draw arms and weapon
            if self.attacking:
                # Attack animation
                weapon_length = self.size * 1.2
                if self.facing_right:
                    arm_angle = -45 + self.attack_frame * 15
                    weapon_start = (self.x + self.size//4, self.y - self.size + self.size//3)
                    weapon_end = (weapon_start[0] + math.cos(math.radians(arm_angle)) * weapon_length,
                                weapon_start[1] + math.sin(math.radians(arm_angle)) * weapon_length)
                else:
                    arm_angle = 225 - self.attack_frame * 15
                    weapon_start = (self.x - self.size//4, self.y - self.size + self.size//3)
                    weapon_end = (weapon_start[0] + math.cos(math.radians(arm_angle)) * weapon_length,
                                weapon_start[1] + math.sin(math.radians(arm_angle)) * weapon_length)

                # Draw weapon
                pygame.draw.line(surface, BLACK, weapon_start, weapon_end, 3)

                # Draw arms in attack position
                pygame.draw.line(surface, BLACK, (self.x, self.y - self.size + self.size//3),
                               weapon_start, 2)
            else:
                # Normal arm position
                arm_offset = math.sin(pygame.time.get_ticks() * 0.01) * 5
                pygame.draw.line(surface, BLACK, (self.x, self.y - self.size + self.size//3),
                               (self.x - self.size//4, self.y - self.size//1.5 + arm_offset), 2)
                pygame.draw.line(surface, BLACK, (self.x, self.y - self.size + self.size//3),
                               (self.x + self.size//4, self.y - self.size//1.5 - arm_offset), 2)

        # Draw health bar
        health_width = 40
        health_height = 5
        health_x = self.x - health_width//2
        health_y = self.y - self.size - 30
        pygame.draw.rect(surface, RED, (health_x, health_y, health_width, health_height), 1)
        pygame.draw.rect(surface, RED, (health_x, health_y, health_width * (self.health/100), health_height))

    def draw_dead(self, surface):
        # Draw fallen stickman
        if self.facing_right:
            # Body
            pygame.draw.line(surface, BLACK, (self.x - self.size//2, self.y),
                           (self.x + self.size//2, self.y), 2)
            # Head
            pygame.draw.circle(surface, BLACK, (self.x + self.size//2, self.y), self.size//4, 2)
            # Legs
            pygame.draw.line(surface, BLACK, (self.x - self.size//2, self.y),
                           (self.x - self.size//4, self.y - self.size//4), 2)
            pygame.draw.line(surface, BLACK, (self.x - self.size//2, self.y),
                           (self.x - self.size//4, self.y + self.size//4), 2)
        else:
            # Mirror image when facing left
            pygame.draw.line(surface, BLACK, (self.x - self.size//2, self.y),
                           (self.x + self.size//2, self.y), 2)
            pygame.draw.circle(surface, BLACK, (self.x - self.size//2, self.y), self.size//4, 2)
            pygame.draw.line(surface, BLACK, (self.x + self.size//2, self.y),
                           (self.x + self.size//4, self.y - self.size//4), 2)
            pygame.draw.line(surface, BLACK, (self.x + self.size//2, self.y),
                           (self.x + self.size//4, self.y + self.size//4), 2)

    def move(self, dx):
        if not self.dead:
            if self.is_dashing:
                dx = self.dash_speed * self.dash_direction
            self.x += dx
            self.x = max(50, min(self.x, WIDTH - 50))  # Keep within screen bounds
            self.facing_right = dx > 0 if dx != 0 else self.facing_right
            
            # Add trail effect when dashing
            if self.is_dashing and not self.dead:
                self.dash_trail.append({
                    'x': self.x,
                    'y': self.y,
                    'alpha': 255
                })
    
    def jump(self):
        if not self.dead and not self.is_jumping:
            self.vel_y = self.jump_power
            self.is_jumping = True
            
    def dash(self, direction):
        if not self.dead and not self.is_dashing and self.dash_cooldown <= 0:
            self.is_dashing = True
            self.dash_duration = 10
            self.dash_direction = direction
            self.dash_cooldown = self.dash_cooldown_max

    def attack(self):
        if not self.dead and not self.attacking:
            self.attacking = True
            self.attack_frame = 0
            
            # Increment combo if within combo window
            if self.combo_timer > 0:
                self.combo_count = (self.combo_count + 1) % self.max_combo
            else:
                self.combo_count = 0
            
            # Reset combo timer
            self.combo_timer = 30  # Frames to perform next combo hit
            
            # Create silver slash effect based on combo
            if self.facing_right:
                start_angle = -45
            else:
                start_angle = 225
                
            if self.combo_count == 0:  # Horizontal slash
                self.slash_effects.append(SlashEffect(
                    self.x + (30 if self.facing_right else -30),
                    self.y - self.size + 20,
                    start_angle,
                    self.size * 1.5,
                    SILVER
                ))
            elif self.combo_count == 1:  # Diagonal slash
                self.slash_effects.append(SlashEffect(
                    self.x + (25 if self.facing_right else -25),
                    self.y - self.size + 30,
                    start_angle + (30 if self.facing_right else -30),
                    self.size * 1.8,
                    SILVER
                ))
            else:  # Vertical power slash
                self.slash_effects.append(SlashEffect(
                    self.x + (20 if self.facing_right else -20),
                    self.y - self.size + 40,
                    start_angle + (60 if self.facing_right else -60),
                    self.size * 2,
                    SILVER
                ))
                
    def aerial_attack(self):
        if not self.dead and not self.attacking and not self.spinning and not self.is_dashing:
            self.is_jumping = True
            self.spinning = True
            self.vel_y = self.jump_power
            self.spin_angle = 0

    def take_damage(self, amount):
        if self.hit_cooldown <= 0:
            # Player takes reduced damage
            if not self.facing_right:  # If player is facing enemy, reduce damage more
                amount *= 0.5  # 50% damage reduction when blocking
            self.health -= amount
            
            # Longer invulnerability for player
            self.hit_cooldown = 45 if not self.facing_right else 30
            
            # Create blood particles
            for _ in range(8):
                # Blood particles shoot out in the direction of the hit
                angle = random.uniform(-math.pi/4, math.pi/4)  # Spread angle
                speed = random.uniform(3, 6)
                self.particles.append(Particle(
                    self.x, self.y - self.size/2,
                    (200, 0, 0),  # Dark red color
                    size=random.randint(2, 3),
                    speed=speed,
                    lifetime=40
                ))
            
            if self.health <= 0:
                self.health = 0
                self.dead = True

    def update(self):
        if self.attacking:
            self.attack_frame += 1
            if self.attack_frame >= 6:
                self.attacking = False
                self.attack_frame = 0

        if self.hit_cooldown > 0:
            self.hit_cooldown -= 1
            
        if self.combo_timer > 0:
            self.combo_timer -= 1
        
        # Update dash
        if self.is_dashing:
            self.dash_duration -= 1
            if self.dash_duration <= 0:
                self.is_dashing = False
        
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1
            
        # Update dash trail
        for trail in self.dash_trail:
            trail['alpha'] -= 15
        self.dash_trail = [t for t in self.dash_trail if t['alpha'] > 0]
            
        # Apply gravity and update position
        if not self.dead:
            self.vel_y += self.gravity
            self.y += self.vel_y
            
            # Update spin and create effects
            if self.spinning:
                self.spin_angle += 20  # Spin speed
                # Create slash effects during spin
                if self.spin_angle % 90 == 0:
                    angle = math.radians(self.spin_angle)
                    self.slash_effects.append(SlashEffect(self.x, self.y, angle, 40, SILVER))
            
            # Ground collision
            if self.y > GROUND_Y:
                self.y = GROUND_Y
                self.vel_y = 0
                self.is_jumping = False
                if self.spinning:
                    self.spinning = False
                    self.spin_angle = 0
                    # Create smoke particles on landing
                    for _ in range(10):
                        self.particles.append(Particle(self.x, GROUND_Y, GRAY, 
                                                    size=random.randint(2,4),
                                                    speed=random.uniform(2,4)))
            
        # Update slash effects and particles
        self.slash_effects = [effect for effect in self.slash_effects if effect.update()]
        self.particles = [p for p in self.particles if p.update()]

def main():
    clock = pygame.time.Clock()
    player = Stickman(100, True)
    
    # List to store dead enemies
    dead_enemies = []
    
    # Enemy wave system
    current_wave = 1
    enemy = Stickman(WIDTH - 100, False)
    enemy.speed = 5  # Base speed
    
    # Score and font
    score = 0
    font = pygame.font.Font(None, 36)
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_z:
                    player.attack()
                elif event.key == pygame.K_SPACE:
                    player.jump()
                elif event.key == pygame.K_x:
                    player.aerial_attack()
                elif event.key == pygame.K_LSHIFT:
                    # Dash in the direction the player is facing or moving
                    keys = pygame.key.get_pressed()
                    if keys[pygame.K_LEFT]:
                        player.dash(-1)
                    elif keys[pygame.K_RIGHT]:
                        player.dash(1)
                    else:
                        player.dash(1 if player.facing_right else -1)

        if player.dead:
            # Game Over screen
            screen.fill(WHITE)
            game_over_text = font.render(f'Game Over - Wave: {current_wave}', True, BLACK)
            score_text = font.render(f'Final Score: {score}', True, BLACK)
            game_over_rect = game_over_text.get_rect(center=(WIDTH/2, HEIGHT/2 - 20))
            score_rect = score_text.get_rect(center=(WIDTH/2, HEIGHT/2 + 20))
            screen.blit(game_over_text, game_over_rect)
            screen.blit(score_text, score_rect)
            pygame.display.flip()
            continue

        # Handle continuous keyboard input
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            player.move(-player.speed)
        if keys[pygame.K_RIGHT]:
            player.move(player.speed)

        # Spawn new enemy if current one is dead
        if enemy.dead and enemy not in dead_enemies:
            dead_enemies.append(enemy)
            score += 100 * current_wave  # More points for higher waves
            current_wave += 1
            
            # Create new enemy with increased stats and random spawn
            spawn_side = random.choice(['left', 'right'])
            if spawn_side == 'left':
                spawn_x = random.randint(50, WIDTH//3)  # Left third of screen
                facing_right = True
            else:
                spawn_x = random.randint(2*WIDTH//3, WIDTH-50)  # Right third of screen
                facing_right = False
                
            enemy = Stickman(spawn_x, facing_right)
            # More gradual speed increase
            enemy.speed = min(5 + current_wave * 0.25, 8)  # Cap speed at 8, slower increase
            # More gradual health increase
            enemy.health = 100 + (current_wave * 5)  # 5 HP per wave instead of 10

        # Enemy AI - gets more aggressive with each wave
        if not enemy.dead:
            if pygame.time.get_ticks() % max(3 - current_wave//10, 2) == 0:  # Slower reaction improvement
                if abs(player.x - enemy.x) < 80 and not enemy.attacking:
                    # More gradual attack chance increase
                    if random.random() < min(0.3 + current_wave * 0.02, 0.6):  # Cap at 60% instead of 80%
                        enemy.attack()
                else:
                    # More gradual speed factor increase
                    speed_factor = min(0.25 + current_wave * 0.05, 0.75)  # Cap at 75% instead of 100%
                    if player.x < enemy.x:
                        enemy.move(-enemy.speed * speed_factor)
                    elif player.x > enemy.x:
                        enemy.move(enemy.speed * speed_factor)

        # Check for hits
        if player.attacking and player.attack_frame == 3:
            if abs(player.x - enemy.x) < 80:
                # Regular attack damage
                enemy.take_damage(20)
        
        # Aerial attack does more damage and has wider range
        if player.spinning:
            if abs(player.x - enemy.x) < 100:  # Larger hit range
                enemy.take_damage(35)  # More damage

        if enemy.attacking and enemy.attack_frame == 3:
            if abs(player.x - enemy.x) < 80:
                # Reduced base damage and slower scaling
                base_damage = 6  # Reduced from 10
                wave_damage = min(current_wave * 0.3, 4)  # Slower scaling, max +4
                player.take_damage(base_damage + wave_damage)

        # Update
        player.update()
        enemy.update()

        # Draw
        screen.fill(WHITE)
        pygame.draw.line(screen, BLACK, (0, GROUND_Y), (WIDTH, GROUND_Y), 2)
        
        # Draw all dead enemies first
        for dead_enemy in dead_enemies:
            dead_enemy.draw(screen)
        
        # Draw current enemy and player
        enemy.draw(screen)
        player.draw(screen)
        
        # Draw wave number and score
        wave_text = font.render(f'Wave: {current_wave}', True, BLACK)
        score_text = font.render(f'Score: {score}', True, BLACK)
        screen.blit(wave_text, (10, 10))
        screen.blit(score_text, (10, 50))
        
        # Update display
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
