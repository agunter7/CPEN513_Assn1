from tkinter import *
from enum import Enum


class NetTest(Enum):
    RED = 0
    YELLOW = 1


class Algorithm(Enum):
    NONE = -1
    DIJKSTRA = 0
    A_STAR = 1


NET_COLOURS = ["red", "brown", "grey", "orange", "purple", "pink", "green", "medium purple", "white"]

active_algorithm = Algorithm.NONE
source_dict = {}  # Keep track of sources to route from to make life easier
wavefront = None
routing_array = []
array_width = 0
array_height = 0
net_dict = {}
active_net = None
text_id_list = []
done_routing = False
target_sink = None
file_path = "../benchmarks/stdcell.infile"


class Net:
    def __init__(self, source=None, sinks=None, num=-1):
        if sinks is None:
            sinks = []
        self.source = source
        self.sinks = sinks
        self.wireCells = []
        self.num = num
        self.sinksRemaining = len(self.sinks)
        self.initRouteComplete = False

        if self.num == -1:
            print("ERROR: assign a net number to the newly-created net!")


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
        self.isOnPath = False
        self.isWire = False
        self.isCandidate = False  # Is the cell a candidate for the current route?
        self.hasPropagated = False  # Has this cell already been used in a wavefront propagation?
        self.dist_from_source = 0
        self.routingValue = 0
        self.next_cell = []  # Can have multiple "next" cells, because wavefront propagates in 4 directions
        self.prev_cell = None

    def get_coords(self): return self.x, self.y


def main():
    global routing_array
    global array_width
    global array_height
    global file_path

    # Read input file
    routing_file = open(file_path, "r")

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
    routing_canvas.focus_set()
    routing_canvas.bind("<Key>", lambda event: key_handler(routing_canvas, event))
    root.mainloop()


def key_handler(routing_canvas, event):
    global active_algorithm

    e_char = event.char
    if e_char == 'a':
        if active_algorithm == Algorithm.NONE:
            active_algorithm = Algorithm.A_STAR
    elif e_char == 'd':
        if active_algorithm == Algorithm.NONE:
            active_algorithm = Algorithm.DIJKSTRA
    elif str.isdigit(e_char):
        algorithm_multistep(routing_canvas, int(e_char))
    else:
        pass


def algorithm_multistep(routing_canvas, n):
    global active_algorithm
    global active_net
    global done_routing
    global net_dict
    global wavefront
    global target_sink

    if active_net is None:
        active_net = net_dict[0]  # Start with the 0th net
    if done_routing:
        # Circuit is complete
        return
    if wavefront is None:
        target_sink, best_start_cell = find_best_routing_pair()
        if active_net.initRouteComplete:
            # Best starting cell has been found via Manhattan Distance to an unrouted sink
            wavefront = [best_start_cell.get_coords()]
        else:
            # Start from source cell by default
            wavefront = [active_net.source.get_coords()]

    if len(wavefront) == 0:
        # No more available cells for wavefront propagation in this net
        # This net cannot be routed
        # Move on to next net
        # TODO: For multi-pin nets, maybe try targeting a new sink (i.e. start propagation from a diff point) instead
        print("Failed to route net " + str(active_net.num) + " with colour " + NET_COLOURS[active_net.num])
        cleanup_candidates(routing_canvas)
        wavefront = None
        if active_net.num + 1 in net_dict.keys():
            # Move to the next net
            active_net = net_dict[active_net.num + 1]
        else:
            # All nets are routed
            print("Circuit complete")
            done_routing = True
        return

    if active_algorithm == Algorithm.DIJKSTRA:
        dijkstra_multistep(routing_canvas, n)
    elif active_algorithm == Algorithm.A_STAR:
        a_star_multistep(routing_canvas, n)
    else:
        return


def find_best_routing_pair():
    global active_net

    if not isinstance(active_net, Net):
        return

    # Start wavefront from the routed point that is closest to the next net
    shortest_dist = float("inf")
    best_start_cell = None
    best_sink = None
    # Separate sinks into routed and unrouted
    unrouted_sinks = [unrouted_sink for unrouted_sink in active_net.sinks if not unrouted_sink.isRouted]
    routed_sinks = [routed_sink for routed_sink in active_net.sinks if routed_sink.isRouted]
    for unrouted_sink in unrouted_sinks:
        if not unrouted_sink.isRouted:
            # Check source cell and routed sinks first
            dist = manhattan_cell(unrouted_sink, active_net.source)
            if dist < shortest_dist:
                shortest_dist = dist
                best_start_cell = active_net.source
                best_sink = unrouted_sink
            for routed_sink in routed_sinks:
                dist = manhattan_cell(unrouted_sink, routed_sink)
                if dist < shortest_dist:
                    shortest_dist = dist
                    best_start_cell = routed_sink
                    best_sink = unrouted_sink
            # Check wire cells
            for wire_cell in active_net.wireCells:
                dist = manhattan_cell(unrouted_sink, wire_cell)
                if dist < shortest_dist:
                    shortest_dist = dist
                    best_start_cell = wire_cell
                    best_sink = unrouted_sink
    return best_sink, best_start_cell


def dijkstra_multistep(routing_canvas, n):
    for _ in range(n):
        dijkstra_step(routing_canvas)


def a_star_multistep(routing_canvas, n):
    for _ in range(n):
        a_star_step(routing_canvas)


def a_star_step(routing_canvas):
    global active_net
    global wavefront
    global target_sink
    global done_routing

    if isinstance(wavefront, list):
        active_wavefront = wavefront.copy()  # Avoid overwrite and loss of data
        wavefront.clear()  # Will have a new wavefront after A* step
    else:
        return

    # Data check
    if not isinstance(target_sink, Cell) or not isinstance(active_net, Net):
        return

    sink_is_found = False
    sink_cell = None
    for cell_coords in active_wavefront:
        if not sink_is_found:
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
                        active_net.sinksRemaining -= 1
                        sink_cell.routingValue = active_cell.dist_from_source+1
                        sink_cell.prev_cell = active_cell
                        active_cell.next_cell.append(sink_cell)
                        break
                    cell_is_viable = not cand_cell.isObstruction and not cand_cell.isCandidate \
                        and not cand_cell.isWire and not cand_cell.isSource and not cand_cell.isSink
                    if cell_is_viable:
                        # Note cell as a candidate for the routing path and add it to the wavefront
                        cand_cell.isCandidate = True
                        cand_cell.dist_from_source = active_cell.dist_from_source+1
                        cand_cell.routingValue = cand_cell.dist_from_source + manhattan_cell(cand_cell, target_sink)
                        cand_cell.prev_cell = active_cell
                        active_cell.next_cell.append(cand_cell)
                        # Edit rect in GUI to show it is in wavefront
                        routing_canvas.itemconfigure(cand_cell.id, fill='black')
                        # Place text inside the rect to show its routing value
                        cell_rect_coords = routing_canvas.coords(cand_cell.id)
                        text_x = (cell_rect_coords[0] + cell_rect_coords[2]) / 2
                        text_y = (cell_rect_coords[1] + cell_rect_coords[3]) / 2
                        text_id = routing_canvas.create_text(text_x, text_y, font=("arial", 10),
                                                             text=str(cand_cell.routingValue), fill='white')
                        text_id_list.append(text_id)  # For later text deletion

    # Build wavefront for next step
    min_route_value = float("inf")
    for column in routing_array:
        for cell in column:
            if cell.isCandidate:
                if not cell.hasPropagated:
                    wavefront.append((cell.x, cell.y))
                    cell.hasPropagated = True
                    if cell.routingValue < min_route_value:
                        min_route_value = cell.routingValue
    # Remove cells from wavefront with large routing values
    wavefront_deletion_indices = []
    for idx, cell_coords in enumerate(wavefront):
        cell_x = cell_coords[0]
        cell_y = cell_coords[1]
        cell = routing_array[cell_x][cell_y]
        if cell.routingValue > min_route_value:
            wavefront_deletion_indices.append(idx)
            cell.hasPropagated = False
    wavefront_deletion_indices.reverse()  # Need to delete higher indices first to avoid index shifting between deletes
    for index in wavefront_deletion_indices:
        del wavefront[index]

    if sink_is_found:
        # Connect sink to source (or other cell in net)
        print("Connecting sink")
        net_is_routed = False
        net_colour = NET_COLOURS[sink_cell.netGroup]  # Needed to colour wires
        backtrace_cell = sink_cell
        while not net_is_routed:
            if ((backtrace_cell.isRouted and active_net.initRouteComplete) or backtrace_cell.isSource) \
                    and backtrace_cell.netGroup == active_net.num:
                # Done
                net_is_routed = True
            elif backtrace_cell.isCandidate:
                backtrace_cell.isCandidate = False
                backtrace_cell.isWire = True
                backtrace_cell.netGroup = active_net.num
                backtrace_cell.isRouted = True
                routing_canvas.itemconfigure(backtrace_cell.id, fill=net_colour)
                active_net.wireCells.append(backtrace_cell)
            elif backtrace_cell.isSink:
                backtrace_cell.isRouted = True
                pass
            else:
                print("ERROR: Bad backtrace occurred!")
                pass
            backtrace_cell = backtrace_cell.prev_cell

        # Clear non-wire cells
        cleanup_candidates(routing_canvas)

        # Clear/increment active variables
        wavefront = None
        if active_net.sinksRemaining < 1:
            if active_net.num + 1 in net_dict.keys():
                # Move to the next net
                active_net = net_dict[active_net.num + 1]
            else:
                # All nets are routed
                print("Circuit complete")
                done_routing = True
        else:
            # Route the next sink
            active_net.initRouteComplete = True

def dijkstra_step(routing_canvas):
    global active_net
    global wavefront
    global text_id_list
    global done_routing

    active_wavefront = []
    if isinstance(wavefront, list):
        active_wavefront = wavefront.copy()  # Avoid overwrite and loss of data
        wavefront.clear()  # Will have a new wavefront after Dijkstra step
    else:
        return

    sink_is_found = False
    sink_cell = None
    for cell_coords in active_wavefront:
        if not sink_is_found:
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
                        active_net.sinksRemaining -= 1
                        sink_cell.routingValue = active_cell.routingValue + 1  # Makes backtrace easier if sink has this
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
        search_cell = sink_cell
        routing_path = [sink_cell]
        while not net_is_routed:
            # Backtrace through shortest path from Dijkstra wavefront propagation
            search_x = search_cell.x
            search_y = search_cell.y
            search_coords = [(search_x, search_y+1), (search_x, search_y-1),
                             (search_x+1, search_y), (search_x-1, search_y)]
            for (route_x, route_y) in search_coords:
                if 0 <= route_x < array_width and 0 <= route_y < array_height:
                    backtrace_cell = routing_array[route_x][route_y]
                    if ((backtrace_cell.isRouted and active_net.initRouteComplete) or backtrace_cell.isSource) \
                            and backtrace_cell.netGroup == active_net.num:
                        # Done
                        net_is_routed = True
                        break
                    if backtrace_cell.isCandidate and backtrace_cell.routingValue == search_cell.routingValue-1:
                        # Cell is a valid wire location
                        # print("Routing through: " + str(backtrace_cell.x) + ", " + str(backtrace_cell.y))
                        backtrace_cell.isCandidate = False
                        backtrace_cell.isWire = True
                        backtrace_cell.netGroup = active_net.num
                        routing_path.append(backtrace_cell)
                        routing_canvas.itemconfigure(backtrace_cell.id, fill=net_colour)
                        active_net.wireCells.append(backtrace_cell)
                        # Continue backtrace from this cell
                        search_cell = backtrace_cell
                        break

        # Mark routed cells as such
        for cell in routing_path:
            cell.isRouted = True

        # Clear non-wire cells
        cleanup_candidates(routing_canvas)

        # Clear/increment active variables
        wavefront = None
        if active_net.sinksRemaining < 1:
            if active_net.num+1 in net_dict.keys():
                # Move to the next net
                active_net = net_dict[active_net.num+1]
            else:
                # All nets are routed
                print("Circuit complete")
                done_routing = True
        else:
            # Route the next sink
            active_net.initRouteComplete = True
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
                cell.hasPropagated = False
                routing_canvas.itemconfigure(cell.id, fill='white')
    # Remove text from all cells (including cells that formed a route)
    for text_id in text_id_list:
        routing_canvas.delete(text_id)


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

    # Add sources and sinks (Note that the routing array already has blank Cells)
    num_nets = routing_file.readline()  # Discard, data not needed
    for net_num, line in enumerate(routing_file):
        net_tokens = line.split(' ')
        num_pins = int(net_tokens[0])
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
                new_net.sinksRemaining += 1
        # Add the new net to the net dictionary
        net_dict[new_net.num] = new_net

    return routing_grid


def manhattan_point(point1: (int, int), point2: (int, int)) -> int:
    """
    Return the Manhattan distance between two points
    :param point1:
    :param point2:
    :return:
    """
    return abs(point1[0] - point2[0]) + abs(point1[1] - point2[1])


def manhattan_cell(cell1: Cell, cell2: Cell) -> int:
    """
    Return the Manhattan distance between two Cells
    :param cell1:
    :param cell2:
    :return:
    """
    return abs(cell1.x - cell2.x) + abs(cell1.y - cell2.y)


if __name__ == "__main__":
    main()
