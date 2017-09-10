"""
Grass and sheep.
"""

import sys, os
import numpy, math
import datetime, logging
from collections import defaultdict
import random, time
import GdoUtility

import sdl2
import sdl2.ext
import sdl2.ext.colorpalettes



logger = None
dim_X = 800
dim_Y = 600
grass = numpy.zeros( (dim_X,dim_Y), dtype=numpy.uint8 )
sheep = set()

grass_colors = {
    0:  (32,32,0),
    8:  (0,192,0),
    16: (0,176,0),
    24: (0,160,0),
    32: (0,144,0),
    40: (4,136,0),
    48: (8,132,0),
    56: (16,128,0),
    64: (32,128,0)
}

grass_colors_2 = {
    0:  (255,0,0),
    8:  (192,64,0),
    16: (128,128,0),
    24: (64,192,0),
    32: (0,255,0),
    40: (0,192,64),
    48: (0,128,128),
    56: (0,64,192),
    64: (0,0,255)
}



class RandomInCircle():
    """
    Cycle through the possible coordinates that fall inside the given range.
    """
    
    def __init__(self, rand_range):
        self.possible_coords = list()
        for x in range(0-rand_range,rand_range+1):
            for y in range(0-rand_range,rand_range+1):
                if x or y:
                    dist = math.sqrt(x**2 + y**2)
                    if dist <= rand_range:
                        self.possible_coords.append((x,y))
                        
        random.shuffle(self.possible_coords)
        self.next_idx = 0
        
    def shuffle(self):
        random.shuffle(self.possible_coords)
        
    def get_next(self):
        self.next_idx += 1
        if self.next_idx >= len(self.possible_coords):
            self.next_idx = 0
        return self.possible_coords[self.next_idx]

        

class Sheep():
    movement_rate = 2
    eating_rate = 1
    voksen_size = 10
    baby_food_requirement = 10

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.movement_points = 0
        self.food_points = 5
        self.gender = random.randint(0,1)
        
    def get_coord(self):
        return (self.x,self.y)
        
    def move_to(self, x, y):
        dist = math.sqrt(x**2 + y**2)
        self.movement_points -= dist
        self.x = x
        self.y = y
        
    def update(self):
        self.x = self.x + random.randint(-1,1)
        self.y = self.y + random.randint(-1,1)
        
        if self.x < 0:
            self.x = 0
        if self.y < 0:
            self.y = 0
        if self.x >= dim_X:
            self.x = dim_X-1
        if self.y >= dim_Y:
            self.y = dim_Y-1
            
        gr_val = grass[self.x,self.y]
        if gr_val:
            gr_val = min(gr_val,10)
            self.food_points + gr_val
            grass[self.x,self.y] -= gr_val
        self.food_points -= 1
        if self.food_points > 100:
            self.food_points = 100
        
    def make_baby(self, other):
        if self.gender == 0 and other.gender == 1 and self.food_points == 100:
            self.food_points = 50
            return Sheep(self.x, self.y)
        return None
            
    def __bool__(self):
        return self.food_points > 0
            
        
        
        
def grow_grass(grass_grower):
    global grass
    
    logger.info("Start grow_grass().")
    start = datetime.datetime.now()
    
    seeds = set()
    updates = set()
    
    grass += 1              # increment all grass
    grass[grass == 1] = 0   # if it has value 1, that means it was 0, send back to zero
    for x,y in numpy.transpose(numpy.nonzero(grass >= 64)):
        grass[x,y] = 58
        newx,newy = grass_grower.get_next()
        newx += x
        newy += y
        if 0 <= newx < dim_X and 0 <= newy < dim_Y:
            seeds.add((newx,newy))
        
    sprout_count = 0
    for seed in seeds:
        if not grass[seed]:
            grass[seed] = 1
            sprout_count += 1
    if sprout_count:
        logger.info("Got %s sprouts from %s seeds (%0.01f%%)." % (sprout_count,len(seeds),100*sprout_count/len(seeds)))
    else:
        logger.info("Got no sprouts from %s seeds." % len(seeds))
    
    # all grass with a value of 1,9,17 etc should get a new color
    updates = set([(x,y) for x,y in numpy.transpose(numpy.nonzero(grass % 8 == 1))])
    
    logger.info("Elapsed time in grow_grass(): %s" % GdoUtility.format_elapsed_seconds(GdoUtility.elapsed_since(start)))
    
    return updates
    
    
    
def do_draw(rend, updates, sheep_coords):
    logger.info("Start do_draw() with %s updates (%0.01f%%) and %s sheep." % (len(updates),100*len(updates)/(dim_X*dim_Y),len(sheep_coords)))
    start = datetime.datetime.now()
    
    colors = defaultdict(lambda: [])
    for coord in updates:
        gr_val = (grass[coord] + 7) // 8 * 8
        colors[gr_val].append(coord[0])
        colors[gr_val].append(coord[1])
            
    # better performance by calling the pixel draw function with lists
    for gr_val,points in colors.items():
        #logger.info("Draw %s items of grass level %s." % (len(points)//2,gr_val))
        rend.draw_point(points=points, color=grass_colors[gr_val])
        
    sheep_coords = [i for j in sheep_coords for i in j]   # list of tuples concatenated into just a list
    rend.draw_point(points=sheep_coords, color=(255,255,255))
        
    logger.info("Elapsed time in do_draw(): %s" % GdoUtility.format_elapsed_seconds(GdoUtility.elapsed_since(start)))



def run():
    global logger
    logger = GdoUtility.setup_logger("life_test.log", console_level=logging.DEBUG)
    
    sdl2.ext.init()
    window = sdl2.ext.Window("Life project", size=(dim_X, dim_Y))
    window.show()

    # explicitly acquire the window's surface to draw on
    windowsurface = window.get_surface()
    rend = sdl2.ext.Renderer(windowsurface)
    sdl2.ext.fill(windowsurface, grass_colors[0])
    
    grass_grower = RandomInCircle(3)
    
    # seed the world
    updates = set()
    for i in range(dim_X*dim_Y//10):
        x = random.randint(0,dim_X-1)
        y = random.randint(0,dim_Y-1)
        grass[x,y] = random.randint(1,63)
        updates.add((x,y))
        
    sheep = set()
    for i in range(10):
        x = random.randint(dim_X//2-5,dim_X//2+5)
        y = random.randint(dim_Y//2-5,dim_Y//2+5)
        sheep.add(Sheep(x,y))

    do_draw(rend, updates=updates, sheep_coords=[s.get_coord() for s in sheep])

    running = True
    do_updates = False
    iterations = 0
    while running:
        events = sdl2.ext.get_events()
        
        if events:
            for event in events:
                if event.type == sdl2.SDL_QUIT:
                    running = False
                    break

                # the user pressed the mouse button (but did not necesarily release it)
                if event.type == sdl2.SDL_MOUSEBUTTONDOWN:
                    do_updates = True
                elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                    do_updates = False
            
        if do_updates:
            iterations += 1
            updates = grow_grass(grass_grower)
            
            logger.info("Draw updates before sheep: %s" % len(updates))
            sheep_locations = defaultdict(lambda: [])
            for one_sheep in sheep:
                updates.add(one_sheep.get_coord())
                one_sheep.update()
                sheep_locations[one_sheep.get_coord()].append(one_sheep)
            logger.info("Draw updates after sheep: %s" % len(updates))
                
            for coord,sheep_list in sheep_locations.items():
                for idx1 in range(len(sheep_list)):
                    for idx2 in range(idx1,len(sheep_list)):
                        baby = sheep_list[idx1].make_baby(sheep_list[idx2])
                        if baby:
                            logger.info("Baby sheep!")
                            sheep.add(baby)
                     
            do_draw(rend,updates,sheep_locations.keys())
                
            grass_grower.shuffle()
            logger.info("Complete with iteration #%s." % iterations)
        else:
            time.sleep(0.01)
            
        window.refresh()

    sdl2.ext.quit()
    return 0

if __name__ == "__main__":
    sys.exit(run())
