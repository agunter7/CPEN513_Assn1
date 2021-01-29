from tkinter import *

NET_COLOURS = ["red", "yellow", "grey", "orange", "purple", "pink", "green", "medium purple", "white"]

source_dict = {}  # Keep track of sources to route from to make life easier
wavefront = None
routing_array = []
array_width = 0
array_height = 0
net_dict = {}
active_net = None
num_nets_to_route = 0
text_id_list = []
done_routing = False


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
    routing_canvas.bind('<ButtonPress-3>', lambda e: dijkstra_multistep(routing_canvas, 5))
    root.mainloop()


def dijkstra_multistep(routing_canvas, n):
    for _ in range(n):
        dijkstra_step(routing_canvas)


def dijkstra_step(routing_canvas):
    global active_net
    global wavefront
    global num_nets_to_route
    global text_id_list
    global done_routing

    if active_net is None:
        active_net = net_dict[0]  # Start with the 0th net
    if done_routing:
        # Circuit is complete
        return
    if wavefront is None:
        wavefront = [active_net.source.get_coords()]  # Start from source cell

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
                if cand_cell.isSink and cand_cell.netGroup is active_net.source.netGroup and \
                        cand_cell.isRouted is False:
                    # This is a sink for the source cell
                    sink_is_found = True
                    sink_cell = cand_cell
                    sink_cell.isRouted = True
                    print("Net " + str(active_net.num) + " sinks " + str(active_net.sinksRemaining))
                    active_net.sinksRemaining -= 1
                    print("Net " + str(active_net.num) + " sinks " + str(active_net.sinksRemaining))
                    sink_cell.routingValue = active_cell.routingValue + 1  # Makes backtrace easier if sink has this
                    print("Found sink")
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
                    text_id = routing_canvas.create_text(text_x, text_y, font=("arial", 10),
                                                         text=str(cand_cell.routingValue), fill='white')
                    text_id_list.append(text_id)  # For later text deletion
    if sink_is_found:
        print("Connecting sink")
        # Connect sink to source
        net_is_routed = False
        net_colour = NET_COLOURS[sink_cell.netGroup]  # Needed to colour wires
        print(net_colour)
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
                    if route_cell.isSource and route_cell.netGroup == active_net.num:
                        # Done
                        net_is_routed = True
                        print("Routed net: " + str(active_net.num))
                        break
                    if route_cell.isCandidate and route_cell.routingValue == search_cell.routingValue-1:
                        # Cell is a valid wire location
                        #print("Routing through: " + str(route_cell.x) + ", " + str(route_cell.y))
                        route_cell.isCandidate = False
                        route_cell.isWire = True
                        route_cell.isRouted = True
                        routing_canvas.itemconfigure(route_cell.id, fill=net_colour)
                        # Continue backtrace from this cell
                        search_cell = route_cell
                        break

        # Clear non-wire cells
        cleanup_candidates(routing_canvas)

        # Clear/increment active variables
        wavefront = None
        print("Remaining: " + str(active_net.sinksRemaining))
        if active_net.sinksRemaining == 0:
            if active_net.num+1 in net_dict.keys():
                # Move to the next net
                print("NEXT")
                active_net = net_dict[active_net.num+1]
            else:
                # All nets are routed
                done_routing = True
        else:
            # Route the next sink

            pass


def cleanup_candidates(routing_canvas):
    global routing_array
    global text_id_list

    # Change routing candidate cells back to default colour
    for column in routing_array:
        for cell in column:
            if cell.isCandidate:
                cell.isCandidate = False
                cell.routingValue = 0
                routing_canvas.itemconfigure(cell.id, fill='white')
    # Remove text from all cells (including cells that formed a route)
    for text_id in text_id_list:
        routing_canvas.delete(text_id)


def dijkstra():
    print("dijkstra")


def create_routing_array(routing_file):
    global num_nets_to_route

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

    # Add sources and sinks (Note that the routing array already has blank Cells)
    num_nets_to_route = int(routing_file.readline())
    for net_num, line in enumerate(routing_file):
        net_tokens = line.split(' ')
        num_pins = int(net_tokens[0])  # Don't really need to use this aside from input verification
        # Add source
        source_x = int(net_tokens[1])
        source_y = int(net_tokens[2])
        source_cell = routing_grid[source_x][source_y]
        source_cell.isSource = True
        source_cell.netGroup = net_num
        source_dict[net_num] = (source_x, source_y)
        new_net = Net(source=source_cell, num=net_num)
        # Add sinks
        for idx in range(3, 3+2*(num_pins-1)):
            if idx % 2 == 1:
                # Create sink cell
                cell_x = int(net_tokens[idx])
                cell_y = int(net_tokens[idx + 1])
                sink_cell = routing_grid[cell_x][cell_y]
                sink_cell.isSink = True
                sink_cell.netGroup = net_num
                # Add sink cell to a net
                new_net.sinks.append(sink_cell)
                print("Net " + str(new_net.num) + " sinks " + str(new_net.sinksRemaining))
                new_net.sinksRemaining += 1
                print("Net " + str(new_net.num) + " sinks " + str(new_net.sinksRemaining))
        # Add the new net to the net dictionary
        net_dict[new_net.num] = new_net

    return routing_grid


class Net:
    def __init__(self, source=None, sinks=None, num=-1):
        if sinks is None:
            sinks = []
        self.source = source
        self.sinks = sinks
        self.num = num
        self.sinksRemaining = len(self.sinks)
        self.initRouteComplete = False


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

    def get_coords(self): return self.x, self.y


if __name__ == "__main__":
    main()
