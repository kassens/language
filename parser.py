import re

# 19
NAME                = 0
DOT                 = 1
CHARACTER_CLASS     = 2
ORDERED_CHOICE      = 3
SEQUENCE            = 4
STRING_LITERAL      = 5
ZERO_OR_MORE        = 6
ONE_OR_MORE         = 7
OPTIONAL            = 8
NEGATIVE_LOOK_AHEAD = 9
POSITIVE_LOOK_AHEAD = 10
ERROR_NAME          = 11
ERROR_CHOICE        = 12

# 33
def parse(aCompiledGrammar, input, name = None):
    print(input)
    node = SyntaxNode("#document", input, 0, 0)
    table = aCompiledGrammar['table']
    nameToUID = aCompiledGrammar['nameToUID']

    name = name or "start";

    # This is a stupid check.
    if 'EOF' in nameToUID:
        table[0] = [SEQUENCE, nameToUID[name], nameToUID["EOF"]];

    if not evaluate(Context(input, table), node, table, 0):
        # This is a stupid check.
        if 'EOF' in nameToUID:
            table[0] = [SEQUENCE, nameToUID["%" + name], nameToUID["EOF"]]

        node.children = []

        evaluate(Context(input, table), node, table, 0)

        def enteredNode(node):
            if node.error:
                print(node.message() + '\n')

        node.traverse(
            traversesTextNodes=False,
            enteredNode=enteredNode
        )

    return node;

# 71
class Context:
    def __init__(self, input, table):
        self.position = 0
        self.input = input
        self.memos = [{} for i in table]

# 80
def evaluate(context, parent, rules, rule_id):
    rule = rules[rule_id]
    ruletype = rule[0]
    input_length = len(context.input)
    memos = context.memos[rule_id]

    uid = context.position

    if uid in memos:
        entry = memos[uid]
        if type(entry) == bool: return entry
        if parent:
            parent.children.append(entry.node)
        context.position = entry.position
        return True

    # 102
    if ruletype == NAME or ruletype == ERROR_NAME:
        error_message = rule[3] if len(rule) > 3 else None
        node = SyntaxNode(rule[1], context.input, context.position, 0,
                error_message)
        if not evaluate(context, node, rules, rule[2]):
            memos[uid] = False
            return False
        node.range.length = context.position - node.range.location
        memos[uid] = {'node': node, 'position': context.position }

        if parent:
            parent.children.append(node)
        return True
    # 119
    elif ruletype == CHARACTER_CLASS:
        if context.position >= len(context.input):
            memos[uid] = False
            return False

        character = context.input[context.position]

        if type(rule[1]) == str:
            rule[1] = re.compile(rule[1])

        if rule[1].match(character):
            if parent:
                parent.children.append(character);
            context.position += 1
            return True
        memos[uid] = False;
        return False
    # 135
    elif ruletype == SEQUENCE:
        for index in range(1, len(rule)):
            if not evaluate(context, parent, rules, rule[index]):
                memos[uid] = False
                return False
        return True
    # 148
    elif ruletype == ORDERED_CHOICE or ruletype == ERROR_CHOICE:
        index = 1
        count = len(rule)
        position = context.position

        for index in range(1, len(rule)):
            # cache opportunity here.
            child_count = parent and len(parent.children)

            if evaluate(context, parent, rules, rule[index]):
                return True

            if parent:
                parent.children = parent.children[:child_count]
            context.position = position;
        memos[uid] = False
        return False

    # 169
    elif ruletype == STRING_LITERAL:
        string = rule[1]
        string_length = len(string)

        if string_length + context.position > input_length:
            memos[uid] = False;
            return False;

        index = 0

        for index in range(0, len(string)):
            if context.input[context.position] != string[index]:
                context.position -= index
                memos[uid] = False
                return False
            context.position += 1
        if parent:
            parent.children.append(string)

        return True;
    # 194
    elif ruletype == DOT:
        if context.position < input_length:
            if parent:
                parent.children.append(context.input[context.position]);
            context.position += 1
            return True;
        memos[uid] = False;
        return False;
    # 204
    elif ruletype == POSITIVE_LOOK_AHEAD or ruletype == NEGATIVE_LOOK_AHEAD:
        position = context.position
        result = evaluate(context, None, rules, rule[1]) == (ruletype == POSITIVE_LOOK_AHEAD)
        context.position = position
        memos[uid] = result
        return result
    # 213
    elif ruletype == ZERO_OR_MORE:
        child = None
        position = context.position
        childCount = parent and len(parent.children)

        while evaluate(context, parent, rules, rule[1]):
            position = context.position
            childCount = parent and len(parent.children)

        context.position = position
        if parent:
            parent.children = parent.children[:childCount]

        return True;

    # 230
    elif ruletype == ONE_OR_MORE:
        position = context.position
        childCount = parent and len(parent.children)
        if not evaluate(context, parent, rules, rule[1]):
            memos[uid] = False;
            context.position = position;
            if parent:
                parent.children = parent.children[:childCount]
            return False
        position = context.position
        childCount = parent and len(parent.children)
        while evaluate(context, parent, rules, rule[1]):
            position = context.position
            childCount = parent and len(parent.children)
        context.position = position
        if parent:
            parent.children = parent.children[:childCount]
        return True;

    # 253
    elif ruletype == OPTIONAL:
        position = context.position
        childCount = parent and len(parent.children)

        if not evaluate(context, parent, rules, rule[1]):
            context.position = position;
            if parent:
                parent.children = parent.children[:childCount]
        return True;

# 269
class SyntaxNode:
    def __init__(self, aName, aSource, aLocation, aLength, anErrorMessage = None):
        self.name = aName;
        self.source = aSource;
        self.range = Range(aLocation, aLength)
        self.children = [];
        self.error = anErrorMessage;

    # 280
    def message(self):
        source = self.source

        lineNumber = source.count('\n', 0, self.range.location) + 1
        line_start = source.rfind('\n', 0, self.range.location) + 1
        line_end = source.find('\n', line_start)

        line = source[line_start:line_end]

        message = line + "\n";

        message += ' ' * (self.range.location - line_start)
        message += '^' * min(self.range.length, len(line)) + "\n"
        message += "ERROR line " + str(lineNumber) + ": " + self.error;

        return message;


    # 310
    def __str__(self, spaces=""):
        string = spaces + self.name + " <" + self.innerText() + "> "
        for child in self.children:
            if type(child) == str:
                string += '\n' + spaces + '\t' + child
            else:
                string += '\n' + child.__str__(spaces + '\t')
        return string

    # 334
    def innerText(self):
        r = self.range
        return repr(self.source[r.location:r.location + r.length])

    # 341
    def traverse(self,
            enteredNode=None,
            exitedNode=None,
            traversesTextNodes=False):
        if not enteredNode or enteredNode(self) != False:
            for child in self.children:
                if type(child) != str:
                    child.traverse(
                            enteredNode=enteredNode,
                            exitedNode=exitedNode,
                            traversesTextNodes=traversesTextNodes);
                elif traversesTextNodes:
                    enteredNode(child)
                    if exitedNode: exitedNode(child)
        if exitedNode: exitedNode(self)

# new
class Range:
    def __init__(self, location, length):
        self.location = location
        self.length = length
    def __str__(self):
        return 'Range(location={0.location}, length={0.length})'.format(self)

import sys
import json

if len(sys.argv) != 2:
    print('1 argument expected')
    exit()

with open(sys.argv[1]) as grammarfile:
    grammar = json.load(grammarfile)

print(parse(grammar, sys.stdin.read()))
