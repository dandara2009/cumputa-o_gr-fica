import pygame
import sys

# Inicialização do Pygame e do Sistema de Áudio com tratamento de segurança
pygame.init()
try:
    pygame.mixer.init()
    AUDIO_DISPONIVEL = True
except Exception:
    AUDIO_DISPONIVEL = False

# Constantes de Configuração da Tela
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_SIZE = 32

# Paleta de Cores Moderna
BG_COLOR = (15, 23, 42)
PLATFORM_COLOR = (51, 65, 85)
PLAYER_COLOR = (34, 197, 94)
CRYSTAL_COLOR = (234, 179, 8)
ENEMY_COLOR = (239, 68, 68)
PORTAL_COLOR = (45, 212, 191)
TEXT_COLOR = (248, 250, 252)

# Matriz do Cenário com espaçamento vertical amplo para saltos confortáveis
WORLD_MAP = [
    "#########################",
    "#P                      #",
    "#                       #",
    "#   ###         C   ### #",
    "#                       #",
    "#  C    #     E     C   #",
    "#####   ###    ##########",
    "#                       #",
    "#                       #",
    "#      C         ###    #",
    "#    #####              #",
    "#                       #",
    "#               C       #",
    "#   #####    ###########",
    "#                       #",
    "#   E       C           #",
    "#########   #####   #####",
    "#           #   #       #",
    "#           #   #       #",
    "#   O       #   #       #",
    "#########################",
]


class Player(pygame.sprite.Sprite):
    """Representa o personagem controlado pelo jogador com física de plataforma."""
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((26, 36), pygame.SRCALPHA)
        pygame.draw.rect(self.image, PLAYER_COLOR, (0, 0, 26, 36), border_radius=6)
        self.rect = self.image.get_rect(topleft=(x, y))
        
        self.vx = 0
        self.vy = 0
        self.speed = 4.5
        self.gravity = 0.55
        self.jump_strength = -10.5
        self.on_ground = False

    def handle_input(self):
        keys = pygame.key.get_pressed()
        self.vx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vx = -self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx = self.speed

    def jump(self):
        if self.on_ground:
            self.vy = self.jump_strength
            self.on_ground = False

    def update(self, platforms):
        self.handle_input()

        # Aplicação da gravidade
        self.vy += self.gravity
        if self.vy > 10:
            self.vy = 10

        # Movimentação e colisão horizontal
        self.rect.x += self.vx
        self.collide_axis(self.vx, 0, platforms)

        # Movimentação e colisão vertical
        self.rect.y += self.vy
        self.on_ground = False
        self.collide_axis(0, self.vy, platforms)

    def collide_axis(self, vx, vy, platforms):
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if vx > 0:
                    self.rect.right = p.rect.left
                elif vx < 0:
                    self.rect.left = p.rect.right
                if vy > 0:
                    self.rect.bottom = p.rect.top
                    self.vy = 0
                    self.on_ground = True
                elif vy < 0:
                    self.rect.top = p.rect.bottom
                    self.vy = 0


class Crystal(pygame.sprite.Sprite):
    """Cristal coletável que pontua e libera o portal."""
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((20, 24), pygame.SRCALPHA)
        pygame.draw.polygon(self.image, CRYSTAL_COLOR, [(10, 0), (20, 12), (10, 24), (0, 12)])
        self.rect = self.image.get_rect(topleft=(x + 6, y + 4))


class Enemy(pygame.sprite.Sprite):
    """Inimigo com patrulhamento horizontal autônomo."""
    def __init__(self, x, y, patrol_range=80):
        super().__init__()
        self.image = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.rect(self.image, ENEMY_COLOR, (0, 0, 30, 30), border_radius=4)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.start_x = x
        self.patrol_range = patrol_range
        self.direction = 1
        self.speed = 1.5

    def update(self):
        self.rect.x += self.speed * self.direction
        if self.rect.x > self.start_x + self.patrol_range:
            self.direction = -1
        elif self.rect.x < self.start_x - self.patrol_range:
            self.direction = 1


class Platform(pygame.sprite.Sprite):
    """Bloco estrutural do cenário."""
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill(PLATFORM_COLOR)
        pygame.draw.rect(self.image, (30, 41, 59), (0, 0, TILE_SIZE, TILE_SIZE), 1)
        self.rect = self.image.get_rect(topleft=(x, y))


class Portal(pygame.sprite.Sprite):
    """Portal de saída para concluir a fase após coletar todos os cristais."""
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((32, 48), pygame.SRCALPHA)
        pygame.draw.rect(self.image, PORTAL_COLOR, (0, 0, 32, 48), border_radius=16)
        self.rect = self.image.get_rect(topleft=(x, y))


class Game:
    """Gerenciador principal do ciclo de vida, estados e lógica do jogo."""
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Missão dos Cristais - Espaçado")
        self.clock = pygame.time.Clock()
        
        self.state = "START"  # START, PLAYING, WIN, GAMEOVER
        self.score = 0
        self.lives = 3
        self.crystals_left = 0
        self.invulnerable_timer = 0
        
        self.reset_game()

    def reset_game(self):
        self.score = 0
        self.lives = 3
        self.invulnerable_timer = 0
        self.load_level()

    def load_level(self):
        self.all_sprites = pygame.sprite.Group()
        self.platforms = pygame.sprite.Group()
        self.crystals = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()

        player_start = (100, 100)
        portal_pos = (100, 100)

        for row_idx, row in enumerate(WORLD_MAP):
            for col_idx, char in enumerate(row):
                x = col_idx * TILE_SIZE
                y = row_idx * TILE_SIZE
                if char == '#':
                    p = Platform(x, y)
                    self.platforms.add(p)
                    self.all_sprites.add(p)
                elif char == 'C':
                    c = Crystal(x, y)
                    self.crystals.add(c)
                    self.all_sprites.add(c)
                elif char == 'E':
                    e = Enemy(x, y)
                    self.enemies.add(e)
                    self.all_sprites.add(e)
                elif char == 'P':
                    player_start = (x, y)
                elif char == 'O':
                    portal_pos = (x, y)

        self.player = Player(player_start[0], player_start[1])
        self.portal = Portal(portal_pos[0], portal_pos[1])
        self.all_sprites.add(self.player)
        self.all_sprites.add(self.portal)

        self.crystals_left = len(self.crystals)

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if self.state == "START":
                    if event.key == pygame.K_RETURN:
                        self.state = "PLAYING"
                elif self.state == "PLAYING":
                    if event.key in [pygame.K_SPACE, pygame.K_UP, pygame.K_w]:
                        self.player.jump()
                elif self.state in ["WIN", "GAMEOVER"]:
                    if event.key == pygame.K_r:
                        self.reset_game()
                        self.state = "PLAYING"

    def update(self):
        if self.state == "PLAYING":
            self.player.update(self.platforms)
            self.enemies.update()

            if self.invulnerable_timer > 0:
                self.invulnerable_timer -= 1

            # Coleta de cristais
            hit_crystals = pygame.sprite.spritecollide(self.player, self.crystals, True)
            for _ in hit_crystals:
                self.score += 10
                self.crystals_left -= 1

            # Colisão com inimigos (com temporizador de invulnerabilidade)
            if self.invulnerable_timer == 0:
                if pygame.sprite.spritecollide(self.player, self.enemies, False):
                    self.lives -= 1
                    self.invulnerable_timer = 90  # 1.5 segundos a 60 FPS
                    if self.lives <= 0:
                        self.state = "GAMEOVER"

            # Queda abaixo da tela
            if self.player.rect.top > SCREEN_HEIGHT:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = "GAMEOVER"
                else:
                    self.player.rect.topleft = (100, 100)
                    self.player.vy = 0

            # Condição de Vitória
            if self.crystals_left == 0 and self.player.rect.colliderect(self.portal.rect):
                self.state = "WIN"

    def draw(self):
        self.screen.fill(BG_COLOR)

        if self.state == "START":
            font_title = pygame.font.SysFont("Arial", 44, bold=True)
            font_inst = pygame.font.SysFont("Arial", 20)
            
            title_surf = font_title.render("MISSÃO DOS CRISTAIS", True, CRYSTAL_COLOR)
            inst_surf = font_inst.render("Pressione ENTER para Iniciar", True, TEXT_COLOR)
            controls_surf = font_inst.render("Movimento: A/D ou Setas | Pular: W, Seta Cima ou Espaço", True, (148, 163, 184))
            
            self.screen.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 200))
            self.screen.blit(inst_surf, (SCREEN_WIDTH // 2 - inst_surf.get_width() // 2, 280))
            self.screen.blit(controls_surf, (SCREEN_WIDTH // 2 - controls_surf.get_width() // 2, 340))

        elif self.state == "PLAYING":
            # Desenha todos os sprites sem deslocamento de câmera (tela fixa)
            for sprite in self.all_sprites:
                if sprite == self.player and self.invulnerable_timer > 0 and (self.invulnerable_timer // 6) % 2 == 0:
                    continue
                self.screen.blit(sprite.image, sprite.rect)

            # HUD (Interface)
            font_hud = pygame.font.SysFont("Arial", 18, bold=True)
            score_text = font_hud.render(f"Pontos: {self.score}", True, TEXT_COLOR)
            lives_text = font_hud.render(f"Vidas: {self.lives}", True, TEXT_COLOR)
            crystals_text = font_hud.render(f"Cristais Restantes: {self.crystals_left}", True, CRYSTAL_COLOR)
            
            self.screen.blit(score_text, (20, 15))
            self.screen.blit(lives_text, (20, 40))
            self.screen.blit(crystals_text, (20, 65))

        elif self.state in ["WIN", "GAMEOVER"]:
            font_end = pygame.font.SysFont("Arial", 40, bold=True)
            font_sub = pygame.font.SysFont("Arial", 20)
            
            msg = "PARABÉNS! VOCÊ VENCEU!" if self.state == "WIN" else "FIM DE JOGO!"
            color = CRYSTAL_COLOR if self.state == "WIN" else ENEMY_COLOR
            
            msg_surf = font_end.render(msg, True, color)
            sub_surf = font_sub.render("Pressione 'R' para Reiniciar", True, TEXT_COLOR)
            
            self.screen.blit(msg_surf, (SCREEN_WIDTH // 2 - msg_surf.get_width() // 2, 220))
            self.screen.blit(sub_surf, (SCREEN_WIDTH // 2 - sub_surf.get_width() // 2, 290))

        pygame.display.flip()


if __name__ == "__main__":
    game = Game()
    game.run()