from tkinter import *

NET_COLOURS = ["red", "yellow", "grey", "orange", "purple", "pink", "green", "medium purple", "white"]

source_dict = {}  # Keep track of sources to route from to make life easier
wavefront = None
routing_array = []
array_width = 0
array_height = 0
active_net_num = None
active_source_cell = None


def main():
    global routing_array
    global array_width
    global array_height

    # Read input file
    routing_file = open("../benchmarks/sydney.infile", "r")

    routing_array = create_routing_array(routing_file)
    array_width = len(routing_array)
    array_height = len(routing_array[0])

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

    # Event bindings and Tkinter start
    routing_canvas.bind('<ButtonPress-1>', lambda e: dijkstra_step(routing_canvas))
    root.mainloop()


def dijkstra_step(routing_canvas):
    global active_net_num
    global wavefront
    global active_source_cell

    if active_net_num is None:
        active_net_num = 0  # Start with 0th net
    source_coords = source_dict[active_net_num]
    if active_source_cell is None:
        source_x = source_coords[0]
        source_y = source_coords[1]
        active_source_cell = routing_array[source_x][source_y]
    if wavefront is None:
        wavefront = [source_coords]  # Start from source cell

    active_wavefront = wavefront.copy()  # Avoid overwrite and loss of data
    wavefront.clear()  # Will have a new wavefront after Dijkstra step

    sink_is_found = False
    sink_cell = None
    for cell_coords in active_wavefront:
        # Get an active cell from the active wavefront
        cell_x = cell_coords[0]
        cell_y = cell_coords[1]
        active_cell = routing_array[cell_x][cell_y]
        # Try to propagate one unit in each cardinal direction from the active cell
        search_coords = [(cell_x, cell_y + 1), (cell_x, cell_y - 1),
                         (cell_x + 1, cell_y), (cell_x - 1, cell_y)]
        for (cand_x, cand_y) in search_coords:
            if 0 <= cand_x < array_width and 0 <= cand_y < array_height:
                cand_cell = routing_array[cand_x][cand_y]  # Candidate cell for routing
                # Check if a sink has been found
                if cand_cell.isSink and cand_cell.netGroup is active_source_cell.netGroup:
                    # This is a sink for the source cell
                    sink_is_found = True
                    sink_cell = cand_cell
                    sink_cell.isRouted = True
                    break
                cell_is_viable = not cand_cell.isObstruction and not cand_cell.isCandidate \
                    and not cand_cell.isWire and not cand_cell.isSource and not cand_cell.isSink
                if cell_is_viable:
                    # Note cell as a candidate for the routing path and add it to the wavefront
                    cand_cell.isCandidate = True
                    cand_cell.routingValue = active_cell.routingValue + 1
                    wavefront.append((cand_x, cand_y))
                    # Edit rect in GUI to show it is in wavefront
                    routing_canvas.itemconfigure(cand_cell.id, fill='black')
                    # Place text inside the rect to show its routing value
                    cell_rect_coords = routing_canvas.coords(cand_cell.id)
                    text_x = (cell_rect_coords[0] + cell_rect_coords[2])/2
                    text_y = (cell_rect_coords[1] + cell_rect_coords[3])/2
                    routing_canvas.create_text(text_x, text_y,
                                               text=str(cand_cell.routingValue), fill='white')
        if sink_is_found:
            # Connect sink to source
            net_is_routed = False
            search_cell = sink_cell
            while not net_is_routed:
                # Backtrace through shortest path from Dijkstra wavefront propagation
                search_x = search_cell.x
                search_y = search_cell.y
                search_coords = [(search_x, search_y+1), (search_x, search_y-1),
                                 (search_x+1, search_y), (search_x-1, search_y)]
                for (route_x, route_y) in search_coords:
                    if 0 <= route_x < array_width and 0 <= route_y < array_height:
                        route_cell = routing_array[route_x][route_y]
                        if route_cell.isSource:
                            # Done
                            net_is_routed = True
                            break
                        if route_cell.isCandidate and route_cell.routingValue == search_cell.routingValue-1:
                            # Cell is a valid wire location
                            route_cell.isCandidate = False
                            route_cell.isWire = True
                            route_cell.isRouted = True
                            routing_canvas.itemconfigure(route_cell.id, fill='blue')
                            # Continue backtrace from this cell
                            search_cell = route_cell

            # Clear non-wire cells

            # Clear/increment active variables


    print("Completed a step")


def dijkstra():
    print("dijkstra")


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
    for cell_x, column in enumerate(routing_grid):
        for cell_y in range(grid_height):
            column.append(Cell(x=cell_x, y=cell_y))

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
        source_dict[net_num] = (source_x, source_y)
        # Add sinks
        for idx in range(3, 3+2*(num_pins-1)):
            if idx % 2 == 1:
                cell_x = int(net_tokens[idx])
                cell_y = int(net_tokens[idx + 1])
                (routing_grid[cell_x][cell_y]).isSink = True
                (routing_grid[cell_x][cell_y]).netGroup = net_num

    return routing_grid


class Net:
    def __init__(self):
        self.source = None
        self.sinks = []


class Cell:
    def __init__(self, x=-1, y=-1, obstruction=False, source=False, sink=False, net_group=-1):

        if obstruction and (source or sink):
            print("Error: Bad cell created!")

        self.x = x
        self.y = y
        self.isObstruction = obstruction
        self.isSource = source
        self.isSink = sink
        self.netGroup = net_group
        self.id = -1
        self.isRouted = False
        self.isWire = False
        self.isCandidate = False  # Is the cell a candidate for the current route?
        self.routingValue = 0


if __name__ == "__main__":
    main()
