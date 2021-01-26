from tkinter import *

NET_COLOURS = ["red", "yellow", "grey", "orange", "purple", "pink", "green", "medium purple", "white"]


def main():
    # Read input file
    routing_file = open("../benchmarks/sydney.infile", "r")

    routing_array, array_width, array_height = create_routing_array(routing_file)

    # Create routing canvas
    root = Tk()
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    cell_length = 15
    routing_canvas = Canvas(root, bg='white', width=array_width*cell_length, height=array_height*cell_length)
    routing_canvas.grid(column=0, row=0, sticky=(N, W, E, S))
    for x in range(array_width):
        for y in range(array_height):
            # Add a rectangle to the canvas
            top_left_x = cell_length * x
            top_left_y = cell_length * y
            bottom_right_x = top_left_x + cell_length
            bottom_right_y = top_left_y + cell_length
            if (routing_array[x][y]).isObstruction:
                rectangle_colour = "blue"
            else:
                net_idx = (routing_array[x][y]).netGroup
                rectangle_colour = NET_COLOURS[net_idx]
            rectangle_coords = (top_left_x, top_left_y, bottom_right_x, bottom_right_y)
            (routing_array[x][y]).id = routing_canvas.create_rectangle(rectangle_coords, fill=rectangle_colour)

    root.mainloop()


def create_routing_array(routing_file):
    grid_line = routing_file.readline()

    # Create the routing grid
    grid_width = int(grid_line.split(' ')[0])
    grid_height = int(grid_line.split(' ')[1])
    routing_grid = []
    # Create grid in column-major order
    for _ in range(grid_width):
        routing_grid.append([])
    # Populate grid with cells
    for column in routing_grid:
        for _ in range(grid_height):
            column.append(Cell())

    # Add cell obstructions
    num_obstructed_cells = int(routing_file.readline())
    for _ in range(num_obstructed_cells):
        obstruction_line = routing_file.readline()
        obstruction_x = int(obstruction_line.split(' ')[0])
        obstruction_y = int(obstruction_line.split(' ')[1])
        (routing_grid[obstruction_x][obstruction_y]).isObstruction = True

    # Add sources and sinks
    num_nets = int(routing_file.readline())  # Don't really need to use this aside from input verification
    for net_num, line in enumerate(routing_file):
        net_tokens = line.split(' ')
        num_pins = int(net_tokens[0])  # Don't really need to use this aside from input verification
        # Add source
        source_x = int(net_tokens[1])
        source_y = int(net_tokens[2])
        (routing_grid[source_x][source_y]).isSource = True
        (routing_grid[source_x][source_y]).netGroup = net_num
        # Add sinks
        for idx in range(3, 3+2*(num_pins-1)):
            if idx % 2 == 1:
                x = int(net_tokens[idx])
                y = int(net_tokens[idx + 1])
                (routing_grid[x][y]).isSink = True
                (routing_grid[x][y]).netGroup = net_num

    return routing_grid, grid_width, grid_height


class Cell:
    def __init__(self, obstruction=False, source=False, sink=False, net_group=-1):

        if obstruction and (source or sink):
            print("Error: Bad cell created!")

        self.isObstruction = obstruction
        self.isSource = source
        self.isSink = sink
        self.netGroup = net_group
        self.id = -1


if __name__ == "__main__":
    main()