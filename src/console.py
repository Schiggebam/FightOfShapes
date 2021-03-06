import sys
import threading
import queue


class ConsoleCommand:
    def __init__(self, name, num_ops, description):
        self.name = name
        self.num_ops = num_ops
        self.description = description



class Console:
    def __init__(self):
        # list of commands:
        self.list_of_commands = []
        self.list_of_commands.append(ConsoleCommand("mark_tile", 2, "[args: x y] Mark a tile using x y grid coordinates"))
        self.list_of_commands.append(ConsoleCommand("set_res", 2, "[args: player_id resources] Set the amount of resources of a player to a value"))
        self.list_of_commands.append(ConsoleCommand("set_scouted", 3, "[args: player_id x_grid y_grid]"))
        self.list_of_commands.append(ConsoleCommand("hl_scouted", 1, "[args: player_id] Highlights all scouted tiles of a player"))
        self.list_of_commands.append(ConsoleCommand("clear_aux", 0, "[no args] clears all auxiliary sprites"))
        self.list_of_commands.append(ConsoleCommand("hl_walkable", 0, "[no args] highlights all walkable tiles"))
        self.list_of_commands.append(ConsoleCommand("switch_ka", 0, "[no args] sets ENABLE_KEYFRAME_ANIMATIONS to true or false"))

        self.input_queue = queue.Queue()
        input_thread = threading.Thread(target=self.add_input)
        input_thread.daemon = True
        input_thread.start()
        self.init_cmd = None

        #self.initial_commands()

    def initial_commands(self, file: str):
        li = []
        with open(file) as f:
            init_cmd = f.readlines()
        init_cmd = [x.strip() for x in init_cmd]
        for e in init_cmd:
            self.handle(e, li)
        return li


    def has_input(self):
        return not self.input_queue.empty()

    def get(self):
        li = []
        s = ""
        while self.has_input():
            s = s + str(self.input_queue.get())
        self.handle(s, li)
        return li

    def handle(self, s, li):
        s_split = s.rstrip().split(" ")  # get rid of newline ops
        if s_split[0] == "help":
            for c in self.list_of_commands:
                print(c.name + " [" + str(c.num_ops) + " operands] : " + c.description)
        else:
            for c in self.list_of_commands:
                if c.name == s_split[0]:
                    if c.num_ops + 1 != len(s_split):
                        print("expect " + str(c.num_ops) + " args! command not executed")
                    else:
                        cmd = [s_split[0]]
                        for i in range(c.num_ops):
                            cmd.append(s_split[1 + i])
                        li.append(tuple(cmd))
                        #
                        # if c.num_ops == 0:
                        #     li.append((s_split[0], "0"))  # because we want to return a tuple in any case
                        # elif c.num_ops == 1:
                        #     li.append((s_split[0], s_split[1]))
                        # elif c.num_ops == 2:
                        #     li.append((s_split[0], s_split[1], s_split[2]))
                        # elif c.num_ops == 3:
                        #     li.append((s_split[0], s_split[1], s_split[2], s_split[3]))
                        # elif c.num_ops == 4:
                        #     li.append((s_split[0], s_split[1], s_split[2], s_split[3], s_split[4]))
                        # elif c.num_ops == 5:
                        #     li.append((s_split[0], s_split[1], s_split[2], s_split[3], s_split[4], s_split[5]))

    def add_input(self):
        while True:
            self.input_queue.put(sys.stdin.read(1))
