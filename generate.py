import sys

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }
        print(self.domains)

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """

        for var in self.crossword.variables:
            for value in self.crossword.words:
                if var.length != len(value):
                    self.domains[var].remove(value)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """

        # revise with overlaps
        revised = False
        overlap = self.crossword.overlaps[x, y]

        for x_var in self.domains[x].copy():
            if all(x_var[overlap[0]] != y_var[overlap[1]] for y_var in self.domains[y]):
                self.domains[x].remove(x_var)
                revised = True
        return revised

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """

        if arcs is None:
            # we begin initial list of all arcs in the problem
            arcs = []
            for var in self.crossword.variables:
                for neighbor in self.crossword.neighbors(var):
                    arcs.append((var, neighbor))

        # we check if the domain is empty
        while len(arcs) > 0:
            # I use the axiom of the ac3 alogithm learnt in Class (X, Y) = Dequeue(queue)
            x, y = arcs.pop(0)
            # we use self.revise as suggested to check if the domain of X is revised
            if self.revise(x, y):
                if len(self.domains[x]) == 0:
                    return False
                else:
                    # We check the neighbors of X to make sure that they are arc consistent
                    for z in self.crossword.neighbors(x):
                        if z != y:
                            arcs.append((z, x))
        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """

        for var in self.domains:
            if var not in assignment:
                return False
        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """

        for var in assignment:
            if len(assignment[var]) != var.length:
                return False

            # we check the neighbors of the variable to make sure that they are consistent (no conflict: overlaps)
            for neighbor in self.crossword.neighbors(var):
                if neighbor in assignment:
                    if assignment[var] == assignment[neighbor]:
                        return False

                    if self.crossword.overlaps[var, neighbor]:
                        x, y = self.crossword.overlaps[var, neighbor]
                        if assignment[var][x] != assignment[neighbor][y]:
                            return False

        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """

        values_var_domain = []
        for value in self.domains[var]:
            cnt = 0
            for neighbor in self.crossword.neighbors(var):
                if neighbor not in assignment:
                    for neighbor_value in self.domains[neighbor]:
                        if neighbor_value != value:
                            cnt += 1

            values_var_domain.append((cnt, value))
        values_var_domain.sort()
        return [value for count, value in values_var_domain]

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """

        for var in self.crossword.variables:
            if var not in assignment:

                min_values = self.order_domain_values(var, assignment)
                if len(min_values) == 0:
                    return None
                if len(min_values) == 1:
                    return var
                else:
                    # there is a tie, choose the variable with the highest degree considering min_values is a list of
                    # tuples of value and count
                    max_deg = 0
                    max_deg_var = 0
                    for value in min_values:
                        degree = 0
                        for neighbor in self.crossword.neighbors(var):
                            if value[0] not in self.domains[neighbor]:
                                degree += 1
                        if degree > max_deg:
                            max_deg = degree
                            max_deg_var = var

                    return max_deg_var

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """

        if self.assignment_complete(assignment):
            return assignment

        unassigned_var = self.select_unassigned_variable(assignment)

        if unassigned_var is None:
            return None

        for value in self.order_domain_values(unassigned_var, assignment):
            assignment[unassigned_var] = value

            # checking consistency of the assignment
            if self.consistent(assignment):
                res = self.backtrack(assignment)
                if res is not None:
                    return res

        return None


def main():
    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
