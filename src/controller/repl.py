import cmd
import shlex
from src.model.micro_operators import MicroOperators
from src.model.id_registry import IDRegistry
from src.model.sample_models import SampleModelError, build_cube_sample, build_plane_sample
from src.model.step_exchange import StepExchangeError, save_step_exchange
from src.model.topology import Edge, Face, HalfEdge, Loop, Vertex, Solid # Import Solid
from src.model.step_io import StepIOError, load_step, save_step
from src.view.cli_output import display_topology # Import display_topology

class BRepCLI(cmd.Cmd):
    intro = 'Welcome to the B-Rep Kernel Modeler CLI. Type help or ? to list commands.\n'
    prompt = '(brep) '
    COMMAND_EXAMPLES = {
        'help': [
            'help',
            'help micro',
        ],
        'micro': [
            'micro mvfs 0 0 0',
            'micro mev #103 #101 1 0 0',
            'micro mef #102 #101 #104',
            'micro mekr #102 #101 #108',
            'micro kemr #121',
        ],
        'disp': [
            'disp topology',
            'disp topology #100',
        ],
        'sample': [
            'sample plane',
            'sample plane 10 5',
            'sample cube',
            'sample cube 10',
            'sample cube 5 --append',
        ],
        'save': [
            'save sample.step',
            'save sample.step #100',
            'save sample.step --unit m',
            'save sample.step --unit mm',
            'save sample.step --internal',
        ],
        'load': [
            'load sample.step',
        ],
        'exit': [
            'exit',
        ],
        'quit': [
            'quit',
            'Ctrl+D',
        ],
    }

    def __init__(self):
        super().__init__()
        self.micro_ops = MicroOperators()
        self.registry = IDRegistry()

    def _count_entities(self):
        counts = {
            'solid': 0,
            'face': 0,
            'loop': 0,
            'vertex': 0,
            'edge': 0,
            'halfedge': 0,
        }

        for obj in self.registry._registry.values():
            if isinstance(obj, Solid):
                counts['solid'] += 1
            elif isinstance(obj, Face):
                counts['face'] += 1
            elif isinstance(obj, Loop):
                counts['loop'] += 1
            elif isinstance(obj, Vertex):
                counts['vertex'] += 1
            elif isinstance(obj, Edge):
                counts['edge'] += 1
            elif isinstance(obj, HalfEdge):
                counts['halfedge'] += 1

        return counts

    def do_help(self, arg):
        'Show command help. Usage: help [command]'
        command = arg.strip().lower()

        if command:
            super().do_help(command)
            examples = self.COMMAND_EXAMPLES.get(command)
            if examples:
                print("\nExamples:")
                for example in examples:
                    print(f"  {example}")
            return

        command_names = sorted(
            name[3:]
            for name in self.get_names()
            if name.startswith('do_') and name != 'do_EOF'
        )

        print('Registered commands:')
        for command_name in command_names:
            method = getattr(self, f'do_{command_name}')
            description = (method.__doc__ or '').strip()
            if description:
                print(f"  {command_name:<8} {description}")
            else:
                print(f"  {command_name}")

        print('\nCommand examples:')
        for command_name in command_names:
            examples = self.COMMAND_EXAMPLES.get(command_name)
            if not examples:
                continue

            print(f"  {command_name}:")
            for example in examples:
                print(f"    {example}")

        print("\nTip: Use 'help <command>' for detailed help and examples.")

    def do_micro(self, arg):
        'Execute micro Euler operators: micro <operator> <args>'
        args = arg.split()
        if not args:
            print("Usage: micro <operator> <args>")
            return

        operator = args[0].lower()
        
        try:
            if operator == 'mvfs':
                if len(args) == 4: # micro mvfs <x> <y> <z>
                    x, y, z = float(args[1]), float(args[2]), float(args[3])
                    solid, vertex, face, loop = self.micro_ops.mvfs(x, y, z)
                    print(f"MVFS successful. Solid: {solid.id}, Vertex: {vertex.id}, Face: {face.id}, Loop: {loop.id}")
                else:
                    print("Usage: micro mvfs <x> <y> <z>")
            elif operator == 'mev':
                if len(args) == 6: # Corrected: operator + 5 arguments
                    loop_id = args[1]
                    vertex_id = args[2]
                    x, y, z = float(args[3]), float(args[4]), float(args[5])
                    edge, new_vertex, he1, he2 = self.micro_ops.mev(loop_id, vertex_id, x, y, z)
                    print(f"MEV successful. Edge: {edge.id}, New Vertex: {new_vertex.id}, HalfEdges: {he1.id}, {he2.id}")
                else:
                    print("Usage: micro mev <loop_id> <vertex_id> <x> <y> <z>")
            elif operator == 'mef':
                if len(args) == 4: # micro mef <face_id> <vertex1_id> <vertex2_id>
                    face_id = args[1]
                    vertex1_id = args[2]
                    vertex2_id = args[3]
                    edge, new_face, he1, he2 = self.micro_ops.mef(face_id, vertex1_id, vertex2_id)
                    print(f"MEF successful. New Edge: {edge.id}, New Face: {new_face.id}, HalfEdges: {he1.id}, {he2.id}")
                else:
                    print("Usage: micro mef <face_id> <vertex1_id> <vertex2_id>")
            elif operator == 'mekr':
                if len(args) == 4: # micro mekr <face_id> <vertex1_id> <vertex2_id>
                    face_id = args[1]
                    vertex1_id = args[2]
                    vertex2_id = args[3]
                    edge, new_inner_loop, he1, he2 = self.micro_ops.mekr(face_id, vertex1_id, vertex2_id)
                    print(f"MEKR successful. New Edge: {edge.id}, New Inner Loop: {new_inner_loop.id}, HalfEdges: {he1.id}, {he2.id}")
                else:
                    print("Usage: micro mekr <face_id> <vertex1_id> <vertex2_id>")
            elif operator == 'kemr':
                if len(args) == 2: # micro kemr <edge_id>
                    edge_id = args[1]
                    modified_loop = self.micro_ops.kemr(edge_id)
                    print(f"KEMR successful. Modified Loop: {modified_loop.id}")
                else:
                    print("Usage: micro kemr <edge_id>")
            else:
                print(f"Unknown micro operator: {operator}")
        except ValueError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def do_disp(self, arg):
        'Display information about entities: disp topology [#<solid_id>]'
        args = arg.split()
        if not args:
            print("Usage: disp <command> <args>")
            return

        command = args[0].lower()

        if command == 'topology':
            solid_id = None
            if len(args) == 2:
                solid_id = args[1]
            
            if solid_id:
                solid = self.registry.get_object(solid_id)
                if isinstance(solid, Solid):
                    display_topology(solid)
                else:
                    print(f"Error: Object with ID {solid_id} is not a Solid.")
            else:
                solids = [obj for obj in self.registry._registry.values() if isinstance(obj, Solid)]
                if not solids:
                    print("No solid found in the registry. Please create one using MVFS.")
                    return

                solids.sort(key=lambda s: int(s.id[1:]) if s.id.startswith('#') and s.id[1:].isdigit() else 10**9)
                for index, solid_obj in enumerate(solids, start=1):
                    if len(solids) > 1:
                        print(f"\n=== Solid {index}/{len(solids)}: {solid_obj.id} ===")
                    display_topology(solid_obj)
        else:
            print(f"Unknown disp command: {command}")

    def do_save(self, arg):
        'Save topology to a STEP file: save <filename.step> [#<solid_id>] [--unit m|mm] [--internal]'
        try:
            args = shlex.split(arg)
        except ValueError as e:
            print(f"Error: {e}")
            return

        use_internal = False
        step_unit = 'm'
        normalized_args = []

        index = 0
        while index < len(args):
            token = args[index]

            if token == '--internal':
                use_internal = True
            elif token.startswith('--unit='):
                step_unit = token.split('=', 1)[1].strip().lower()
            elif token == '--unit':
                if index + 1 >= len(args):
                    print("Usage: save <filename.step> [#<solid_id>] [--unit m|mm] [--internal]")
                    return
                step_unit = args[index + 1].strip().lower()
                index += 1
            else:
                normalized_args.append(token)
            index += 1

        if len(normalized_args) not in (1, 2):
            print("Usage: save <filename.step> [#<solid_id>] [--unit m|mm] [--internal]")
            return

        file_path = normalized_args[0]
        solid_id = normalized_args[1] if len(normalized_args) == 2 else None

        try:
            if use_internal:
                saved_solid_id = save_step(file_path, self.registry, solid_id)
                print(
                    f"Save successful (internal format). "
                    f"Solid: {saved_solid_id}, File: {file_path}"
                )
            else:
                saved_solid_ids = save_step_exchange(
                    file_path,
                    self.registry,
                    solid_id,
                    unit=step_unit,
                )
                print(
                    f"Save successful (standard STEP ADVANCED_BREP, unit={step_unit}). "
                    f"Solids: {', '.join(saved_solid_ids)}, File: {file_path}"
                )
        except (ValueError, StepIOError, StepExchangeError) as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def do_sample(self, arg):
        'Create predefined sample models: sample <plane|cube> [size|width depth] [--append]'
        try:
            args = shlex.split(arg)
        except ValueError as e:
            print(f"Error: {e}")
            return

        if not args:
            print("Usage: sample <plane|cube> [size|width depth] [--append]")
            return

        append_mode = '--append' in args
        args = [token for token in args if token != '--append']

        if not args:
            print("Usage: sample <plane|cube> [size|width depth] [--append]")
            return

        sample_name = args[0].lower()

        try:
            if sample_name == 'plane':
                if len(args) == 1:
                    result = build_plane_sample(self.registry, reset_registry=not append_mode)
                elif len(args) == 2:
                    width = float(args[1])
                    result = build_plane_sample(
                        self.registry,
                        width=width,
                        depth=width,
                        reset_registry=not append_mode,
                    )
                elif len(args) == 3:
                    width = float(args[1])
                    depth = float(args[2])
                    result = build_plane_sample(
                        self.registry,
                        width=width,
                        depth=depth,
                        reset_registry=not append_mode,
                    )
                else:
                    print("Usage: sample plane [width depth] [--append]")
                    return

                solid = result['solid']
                bounded_face = result['bounded_face']
                print(f"Plane sample created. Solid: {solid.id}, Bounded Face: {bounded_face.id}")

            elif sample_name == 'cube':
                if len(args) == 1:
                    result = build_cube_sample(self.registry, reset_registry=not append_mode)
                elif len(args) == 2:
                    size = float(args[1])
                    result = build_cube_sample(
                        self.registry,
                        size=size,
                        reset_registry=not append_mode,
                    )
                else:
                    print("Usage: sample cube [size] [--append]")
                    return

                solid = result['solid']
                print(f"Cube sample created. Solid: {solid.id}")

            else:
                print(f"Unknown sample type: {sample_name}")
                print("Available samples: plane, cube")
                return

            counts = self._count_entities()
            print(
                "Entities -> "
                f"Solids: {counts['solid']}, "
                f"Faces: {counts['face']}, "
                f"Loops: {counts['loop']}, "
                f"Vertices: {counts['vertex']}, "
                f"Edges: {counts['edge']}, "
                f"HalfEdges: {counts['halfedge']}"
            )

        except (ValueError, SampleModelError) as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def do_load(self, arg):
        'Load topology from internal format file: load <filename.step>'
        try:
            args = shlex.split(arg)
        except ValueError as e:
            print(f"Error: {e}")
            return

        if len(args) != 1:
            print("Usage: load <filename.step>")
            return

        file_path = args[0]

        try:
            solid_ids = load_step(file_path, self.registry)
            print(f"Load successful. Solids: {', '.join(solid_ids)}")
        except (ValueError, StepIOError) as e:
            print(f"Error: {e}")
            print("Tip: 'load' supports files saved with 'save --internal'.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def do_exit(self, arg):
        'Exit the CLI: exit'
        print('Thank you for using the B-Rep Kernel Modeler CLI.')
        return True

    def do_quit(self, arg):
        'Exit the CLI: quit'
        return self.do_exit(arg)

    def do_EOF(self, arg):
        'Exit the CLI: Ctrl+D'
        print()
        return self.do_exit(arg)