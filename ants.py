import pygame
import random
import math
from pyqtree import Index

# Constants
FOOD_GRABBED_PER_TICK=50
CARRY_CAPACITY = 300
WIDTH, HEIGHT = 800, 600
ANT_SIZE = 4
ANT_COLOR = (255, 0, 0)
PLANT_COLOR = (0, 255, 0)
MAX_PLANT_SIZE = 10000
PLANT_SCALE=1000
INITIAL_PLANT_SIZE = MAX_PLANT_SIZE // 2
GROWTH_RATE = 10
INITIAL_ANTS = 100
LIFE_SPAN = 1000
NEST_POS = (WIDTH // 2, HEIGHT // 2)
GRID_SIZE = 10
GRID_WIDTH = WIDTH // GRID_SIZE
GRID_HEIGHT = HEIGHT // GRID_SIZE
PHEROMONE_DECAY = 0.99
PHEROMONE_COLOR = (0, 255, 255)

class PheromoneGrid:
    def __init__(self):
        self.grid = [[0 for _ in range(GRID_HEIGHT)] for _ in range(GRID_WIDTH)]

    def add_pheromone(self, x, y, amount, food_carried):
        grid_x = int(x // GRID_SIZE) % GRID_WIDTH
        grid_y = int(y // GRID_SIZE) % GRID_HEIGHT
        self.grid[grid_x][grid_y] += amount * (1 + food_carried * 0.2)  # Add a factor based on the food carried

    def get_pheromone(self, x, y):
        grid_x = int(x // GRID_SIZE) % GRID_WIDTH
        grid_y = int(y // GRID_SIZE) % GRID_HEIGHT
        return self.grid[grid_x][grid_y]

    def decay(self):
        for x in range(GRID_WIDTH):
            for y in range(GRID_HEIGHT):
                self.grid[x][y] *= PHEROMONE_DECAY
class Rock:
    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius

class Ant:
    def __init__(self):
        self.x = NEST_POS[0]
        self.y = NEST_POS[1]
        self.life = LIFE_SPAN
        self.full = False
        self.angle = random.uniform(0, 2 * math.pi)  # Add this line
        self.food_carried = 0  # Add this line
        self.target_plant = None

    def feed(self):
        if self.food_carried > 0 and self.life < LIFE_SPAN:
            self.life = min(LIFE_SPAN, self.life + 2)
            self.food_carried -= 1
            if self.food_carried == 0:
                self.full = False

    def move(self, plants, pheromone_grid, ants, quadtree, rocks):

        ant= self
        # Wrap around the screen
        self.x = self.x % WIDTH
        self.y = self.y % HEIGHT

        if ant.target_plant and ant.target_plant.size <= 0:
            ant.target_plant = None

        colliding_with_rock = False
        for rock in rocks:
            if self.check_collision(rock):
                colliding_with_rock = True
                break

        if colliding_with_rock:
            # If colliding with a rock, reverse the direction
            angle = self.angle+math.pi
        elif self.full:
            # send the ant back to the nest
            angle = math.atan2(NEST_POS[1] - self.y, NEST_POS[0] - self.x)
        elif ant.target_plant and ant.target_plant.size > 0:
            angle = math.atan2(ant.target_plant.y - self.y, ant.target_plant.x - self.x)

        else:
            angle = self.follow_pheromones(pheromone_grid)

        self.x += math.cos(angle)
        self.y += math.sin(angle)

        self.feed()

        self.life -= 1

        pheromone_grid.add_pheromone(self.x, self.y, 1, self.food_carried)
        if not ant.full:
            if ant.target_plant:
                plant = ant.target_plant
                if ant.check_collision(plant):
                    food_taken = min(FOOD_GRABBED_PER_TICK, plant.size)
                    plant.consume(food_taken, plants)
                    self.food_carried += food_taken

                if self.food_carried >= CARRY_CAPACITY:
                    ant.full = True
                    ant.target_plant = None

            else:
                query_rect = (self.x - ANT_SIZE, self.y - ANT_SIZE, self.x + ANT_SIZE, self.y + ANT_SIZE)
                nearby_plants = quadtree.intersect(query_rect)
                for plant in nearby_plants:
                    if ant.check_collision(plant):
                        ant.target_plant = plant
                        break

        elif math.dist((ant.x, ant.y), NEST_POS) < 1:
            ants_to_create = round(ant.food_carried // 100)
            ants.extend([Ant() for _ in range(ants_to_create)])
            ant.food_carried = 0
            ant.full = False

        if ant.life <= 0:
            ants.remove(ant)

    def follow_pheromones(self, pheromone_grid):
        max_pheromone = -1
        max_angle = self.angle  # Use the current angle as the initial max_angle

        for angle_offset in range(-90, 90, 10):
            angle = self.angle + math.radians(angle_offset)
            dx = math.cos(angle)
            dy = math.sin(angle)
            x = self.x + dx * GRID_SIZE
            y = self.y + dy * GRID_SIZE
            pheromone = pheromone_grid.get_pheromone(x, y) + random.uniform(0, 1)

            if pheromone > max_pheromone:
                max_pheromone = pheromone
                max_angle = angle

        return max_angle

    def check_collision(self, obj):
        if hasattr(obj,'radius'):
            return math.dist((self.x, self.y), (obj.x, obj.y)) < obj.radius
        else:
            plant= obj
            return math.dist((self.x, self.y), (plant.x, plant.y)) < (plant.size // PLANT_SCALE) + 10

class Plant:
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size


    def __str__(self):
        return f"Plant(x:{self.x},y:{self.y},size:{self.size})"

    def grow(self,plants):
        if self.size < MAX_PLANT_SIZE:
            self.size += GROWTH_RATE
        else:
            self.propagate(plants)

    def propagate(self,plants):
        self.size -= INITIAL_PLANT_SIZE
        x = random.randint(50, WIDTH - 50)
        y = random.randint(50, HEIGHT - 50)
        plants.append(Plant(x, y, INITIAL_PLANT_SIZE))


    def consume(self, amount,plants):
        self.size -= amount
        if self.size <= 0:
            plants.remove(self)


def draw_pheromone_grid(screen, pheromone_grid):
    max_pheromone = max(max(row) for row in pheromone_grid.grid)
    pheromone_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    for x in range(GRID_WIDTH):
        for y in range(GRID_HEIGHT):
            pheromone = pheromone_grid.get_pheromone(x * GRID_SIZE, y * GRID_SIZE)
            alpha = int((pheromone / max_pheromone) * 255)
            color = (*PHEROMONE_COLOR, alpha)
            rect = pygame.Rect(x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
            pygame.draw.rect(pheromone_surface, color, rect)

    screen.blit(pheromone_surface, (0, 0))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Ant Colony Optimization")
    bbox = (0, 0, WIDTH, HEIGHT)
    ants = [Ant() for _ in range(INITIAL_ANTS)]
    plants = [Plant(random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 50), INITIAL_PLANT_SIZE) for _ in range(10)]
    pheromone_grid = PheromoneGrid()
    rocks = [Rock(random.randint(100, WIDTH - 100), random.randint(100, HEIGHT - 100), random.randint(20, 40)) for _ in range(10)]

    running = True
    while running:
        screen.fill((0, 0, 0))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        quadtree = Index(bbox)
        for plant in plants:
            plant.grow(plants)
            bbox = (plant.x, plant.y, plant.x + (plant.size // PLANT_SCALE) + 1, plant.y + (plant.size // PLANT_SCALE)+1)
            quadtree.insert(plant, bbox)

        for ant in ants:
            ant.move(plants, pheromone_grid, ants, quadtree,rocks)
        pheromone_grid.decay()


        draw_pheromone_grid(screen, pheromone_grid)  # Add this line

        for ant in ants: pygame.draw.circle(screen, ANT_COLOR, (int(ant.x), int(ant.y)), ANT_SIZE)

        for plant in plants: pygame.draw.circle(screen, PLANT_COLOR, (int(plant.x), int(plant.y)), plant.size // PLANT_SCALE)
        for rock in rocks:
            pygame.draw.circle(screen, (128, 128, 128), (int(rock.x), int(rock.y)), rock.radius)

        pygame.display.flip()
        pygame.time.delay(20)

main()
