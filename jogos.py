import pygame
import sys
import math
import random


pygame.init()
try:
    pygame.mixer.init()
except Exception:
    pass


SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Defesa Orbital")
clock = pygame.time.Clock()

# Cores
BG_COLOR = (10, 14, 23)
TEXT_COLOR = (255, 255, 255)
PLAYER_COLOR = (59, 130, 246)
PROJECTILE_COLOR = (250, 204, 21)
ENEMY_STRAIGHT_COLOR = (239, 68, 68)
ENEMY_CHASE_COLOR = (168, 85, 247)
HUD_BAR_COLOR = (34, 197, 94)
HUD_BG_COLOR = (51, 65, 85)


class Player(pygame.sprite.Sprite):
    """Nave controlada pelo jogador com rotação em direção ao mouse e movimentação normalizada."""
    def __init__(self, x, y):
        super().__init__()
        self.original_image = pygame.Surface((36, 36), pygame.SRCALPHA)
        
        pygame.draw.polygon(self.original_image, PLAYER_COLOR, [(4, 2), (32, 18), (4, 34), (12, 18)])
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.math.Vector2(x, y)
        
        self.speed = 300  # pixels por segundo
        self.max_hp = 100
        self.hp = 100
        self.invulnerable_timer = 0

    def update(self, dt):
        
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= dt

        keys = pygame.key.get_pressed()
        move_dir = pygame.math.Vector2(0, 0)
        
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move_dir.x -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move_dir.x += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            move_dir.y -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            move_dir.y += 1

        
        if move_dir.length_squared() > 0:
            move_dir = move_dir.normalize()
            self.pos += move_dir * self.speed * dt

        
        self.pos.x = max(20, min(SCREEN_WIDTH - 20, self.pos.x))
        self.pos.y = max(20, min(SCREEN_HEIGHT - 20, self.pos.y))
        self.rect.center = (round(self.pos.x), round(self.pos.y))

        
        mouse_pos = pygame.math.Vector2(pygame.mouse.get_pos())
        direction = mouse_pos - self.pos
        if direction.length_squared() > 0:
            angle = math.degrees(math.atan2(-direction.y, direction.x))
            self.image = pygame.transform.rotate(self.original_image, angle)
            self.rect = self.image.get_rect(center=self.rect.center)


class Projectile(pygame.sprite.Sprite):
    """Projétil disparado pela nave em direção ao cursor."""
    def __init__(self, x, y, target_pos):
        super().__init__()
        self.image = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(self.image, PROJECTILE_COLOR, (4, 4), 4)
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.math.Vector2(x, y)
        
        direction = pygame.math.Vector2(target_pos) - self.pos
        if direction.length_squared() > 0:
            self.velocity = direction.normalize() * 600  # 600 pixels por segundo
        else:
            self.velocity = pygame.math.Vector2(600, 0)

    def update(self, dt):
        self.pos += self.velocity * dt
        self.rect.center = (round(self.pos.x), round(self.pos.y))
        
        
        if not SCREEN_RECT.colliderect(self.rect):
            self.kill()


class EnemyStraight(pygame.sprite.Sprite):
    """Inimigo que se desloca em linha reta em direção ao lado esquerdo."""
    def __init__(self, x, y, speed):
        super().__init__()
        self.image = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.rect(self.image, ENEMY_STRAIGHT_COLOR, (0, 0, 30, 30), border_radius=6)
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.math.Vector2(x, y)
        self.speed = speed

    def update(self, dt, player_pos):
        
        self.pos.x -= self.speed * dt
        self.rect.center = (round(self.pos.x), round(self.pos.y))
        if self.rect.right < 0:
            self.kill()


class EnemyChase(pygame.sprite.Sprite):
    """Inimigo que persegue continuamente a posição atual do jogador."""
    def __init__(self, x, y, speed):
        super().__init__()
        self.image = pygame.Surface((26, 26), pygame.SRCALPHA)
        pygame.draw.circle(self.image, ENEMY_CHASE_COLOR, (13, 13), 13)
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.math.Vector2(x, y)
        self.speed = speed

    def update(self, dt, player_pos):
        direction = pygame.math.Vector2(player_pos) - self.pos
        if direction.length_squared() > 0:
            direction = direction.normalize()
            self.pos += direction * self.speed * dt
        self.rect.center = (round(self.pos.x), round(self.pos.y))


SCREEN_RECT = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)


class Game:
    """Gerenciador principal do jogo, ondas, estados, interface e regras."""
    def __init__(self):
        self.state = "START"  
        self.score = 0
        self.wave = 1
        
        
        self.all_sprites = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        
        self.player = Player(100, SCREEN_HEIGHT // 2)
        self.all_sprites.add(self.player)
        
        
        self.waves_data = {
            1: {"straight_count": 5, "chase_count": 2, "straight_speed": 180, "chase_speed": 110, "spawn_delay": 1.5},
            2: {"straight_count": 8, "chase_count": 5, "straight_speed": 220, "chase_speed": 140, "spawn_delay": 1.2},
            3: {"straight_count": 12, "chase_count": 8, "straight_speed": 260, "chase_speed": 170, "spawn_delay": 0.9}
        }
        
        self.setup_wave()
        self.shoot_cooldown = 0  

    def setup_wave(self):
        data = self.waves_data[self.wave]
        self.enemies_to_spawn = ["straight"] * data["straight_count"] + ["chase"] * data["chase_count"]
        random.shuffle(self.enemies_to_spawn)
        self.spawn_timer = 0
        self.spawn_delay = data["spawn_delay"]
        self.wave_fully_spawned = False

    def reset_game(self):
        self.score = 0
        self.wave = 1
        self.player = Player(100, SCREEN_HEIGHT // 2)
        self.projectiles.empty()
        self.enemies.empty()
        self.all_sprites.empty()
        self.all_sprites.add(self.player)
        self.shoot_cooldown = 0
        self.setup_wave()

    def run(self):
        while True:
            dt = clock.tick(60) / 1000.0  # Delta time em segundos
            self.handle_events(dt)
            self.update(dt)
            self.draw()

    def handle_events(self, dt):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if self.state == "START":
                    if event.key == pygame.K_RETURN:
                        self.state = "PLAYING"
                elif self.state == "PLAYING":
                    if event.key == pygame.K_p:
                        self.state = "PAUSED"
                elif self.state == "PAUSED":
                    if event.key == pygame.K_p:
                        self.state = "PLAYING"
                elif self.state in ["WIN", "GAMEOVER"]:
                    if event.key == pygame.K_r:
                        self.reset_game()
                        self.state = "PLAYING"

        
        if self.state == "PLAYING":
            if self.shoot_cooldown > 0:
                self.shoot_cooldown -= dt * 1000  # converte para milissegundos

            mouse_pressed = pygame.mouse.get_pressed()
            if mouse_pressed[0] and self.shoot_cooldown <= 0:
                self.shoot_cooldown = 250  # 250 ms de intervalo mínimo
                proj = Projectile(self.player.rect.centerx, self.player.rect.centery, pygame.mouse.get_pos())
                self.projectiles.add(proj)
                self.all_sprites.add(proj)

    def update(self, dt):
        if self.state != "PLAYING":
            return

        
        if len(self.enemies_to_spawn) > 0:
            self.spawn_timer += dt
            if self.spawn_timer >= self.spawn_delay:
                self.spawn_timer = 0
                enemy_type = self.enemies_to_spawn.pop(0)
                data = self.waves_data[self.wave]
                spawn_y = random.randint(50, SCREEN_HEIGHT - 50)
                if enemy_type == "straight":
                    enemy = EnemyStraight(SCREEN_WIDTH + 30, spawn_y, data["straight_speed"])
                else:
                    enemy = EnemyChase(SCREEN_WIDTH + 30, spawn_y, data["chase_speed"])
                self.enemies.add(enemy)
                self.all_sprites.add(enemy)
        else:
            self.wave_fully_spawned = True

        
        self.player.update(dt)
        self.projectiles.update(dt)
        self.enemies.update(dt, self.player.rect.center)

        
        collisions = pygame.sprite.groupcollide(self.projectiles, self.enemies, True, True)
        for proj, hit_enemies in collisions.items():
            for enemy in hit_enemies:
                self.score += 25

        
        if self.player.invulnerable_timer <= 0:
            hit_by_enemy = pygame.sprite.spritecollide(self.player, self.enemies, False)
            if hit_by_enemy:
                self.player.hp -= 20
                self.player.invulnerable_timer = 1.0  # 1 segundo de invulnerabilidade
                if self.player.hp <= 0:
                    self.state = "GAMEOVER"

        
        if self.wave_fully_spawned and len(self.enemies) == 0:
            if self.wave < 3:
                self.wave += 1
                self.setup_wave()
            else:
                self.state = "WIN"

    def draw(self):
        screen.fill(BG_COLOR)

        if self.state == "START":
            font_title = pygame.font.SysFont("Arial", 44, bold=True)
            font_inst = pygame.font.SysFont("Arial", 20)
            
            title_surf = font_title.render("DEFESA ORBITAL", True, PROJECTILE_COLOR)
            inst_surf = font_inst.render("Pressione ENTER para Iniciar", True, TEXT_COLOR)
            controls_surf = font_inst.render("Movimento: W, A, S, D | Mira: Mouse | Atirar: Clique Esquerdo | Pausa: P", True, (148, 163, 184))
            
            screen.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 180))
            screen.blit(inst_surf, (SCREEN_WIDTH // 2 - inst_surf.get_width() // 2, 260))
            screen.blit(controls_surf, (SCREEN_WIDTH // 2 - controls_surf.get_width() // 2, 320))

        elif self.state in ["PLAYING", "PAUSED"]:
            
            for sprite in self.all_sprites:
                if sprite == self.player and self.player.invulnerable_timer > 0 and (pygame.time.get_ticks() // 100) % 2 == 0:
                    continue
                screen.blit(sprite.image, sprite.rect)

            
            font_hud = pygame.font.SysFont("Arial", 18, bold=True)
            score_text = font_hud.render(f"Pontos: {self.score}", True, TEXT_COLOR)
            wave_text = font_hud.render(f"Onda: {self.wave} / 3", True, PROJECTILE_COLOR)
            
            screen.blit(score_text, (20, 15))
            screen.blit(wave_text, (20, 45))

            
            bar_x, bar_y, bar_w, bar_h = 20, 75, 180, 16
            pygame.draw.rect(screen, HUD_BG_COLOR, (bar_x, bar_y, bar_w, bar_h), border_radius=4)
            current_hp_w = max(0, int(bar_w * (self.player.hp / self.player.max_hp)))
            if current_hp_w > 0:
                pygame.draw.rect(screen, HUD_BAR_COLOR, (bar_x, bar_y, current_hp_w, bar_h), border_radius=4)
            hp_text = font_hud.render(f"Vida: {self.player.hp}%", True, TEXT_COLOR)
            screen.blit(hp_text, (bar_x + bar_w + 10, bar_y - 2))

            if self.state == "PAUSED":
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 150))
                screen.blit(overlay, (0, 0))
                font_pause = pygame.font.SysFont("Arial", 40, bold=True)
                pause_surf = font_pause.render("JOGO PAUSADO (P para Continuar)", True, TEXT_COLOR)
                screen.blit(pause_surf, (SCREEN_WIDTH // 2 - pause_surf.get_width() // 2, SCREEN_HEIGHT // 2 - 20))

        elif self.state in ["WIN", "GAMEOVER"]:
            font_end = pygame.font.SysFont("Arial", 40, bold=True)
            font_sub = pygame.font.SysFont("Arial", 20)
            
            msg = "MISSÃO CUMPRIDA! VITÓRIA!" if self.state == "WIN" else "ESTAÇÃO DESTRUÍDA! FIM DE JOGO!"
            color = PROJECTILE_COLOR if self.state == "WIN" else ENEMY_STRAIGHT_COLOR
            
            msg_surf = font_end.render(msg, True, color)
            sub_surf = font_sub.render("Pressione 'R' para Reiniciar", True, TEXT_COLOR)
            
            screen.blit(msg_surf, (SCREEN_WIDTH // 2 - msg_surf.get_width() // 2, 220))
            screen.blit(sub_surf, (SCREEN_WIDTH // 2 - sub_surf.get_width() // 2, 290))

        pygame.display.flip()


if __name__ == "__main__":
    game = Game()
    game.run()