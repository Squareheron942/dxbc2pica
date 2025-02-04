import output
from typing import Callable

def parse(line) -> str | list[str]:
    # remove leading and trailing whitespace
    line = line.strip()
    
    if line == '': # ignore empty lines
        return ''
    
    # handle comments
    if line.startswith('//'):
        return _comment(line[3:])
    
    # handle version
    if line.startswith('vs_'):
        return _parse_version(line)
    components = line.replace(',', '').split()
    opcode = components[0].split("_")
    operands = components[1:]
    opbase = [op.split('.')[0] for op in operands]
    
    return list(
        filter(
            None, 
            [
                f'.out {op} {_outputstoname[op]}\n' 
                for op in opbase
                if op in _possibleoutputs and not _setoutputused(op)
            ] + 
            _instr[opcode[0]](opcode, operands)
        )
    )

def clearstate():
    for key in _outputsused.keys():
        _outputsused[key] = False
    
    
_comment = lambda comment = '': '\n'.join(['; ' + line for line in comment.split('\n')]) + '\n'

_outputsused: dict[str, bool] = {
    'oPos': False,
    'oD0': False,
    'oT0': False,
    'oT1': False,
    'oT2': False,
}

_outputstoname: dict[str, str] = {
    'oPos': 'position',
    'oD0': 'color',
    'oT0': 'texcoord0',
    'oT1': 'texcoord1',
    'oT2': 'texcoord2',
}

_invalidoutputs: dict[str, Callable[None, None]] = {
    'oD1': lambda: (_ for _ in ()).throw(Exception('More than 1 color output register not supported')),
    'oT3': lambda: (_ for _ in ()).throw(Exception('More than 3 texcoord output registers not supported')),
    'oT4': lambda: (_ for _ in ()).throw(Exception('More than 3 texcoord output registers not supported')),
    'oT5': lambda: (_ for _ in ()).throw(Exception('More than 3 texcoord output registers not supported')),
    'oT6': lambda: (_ for _ in ()).throw(Exception('More than 3 texcoord output registers not supported')),
    'oT7': lambda: (_ for _ in ()).throw(Exception('More than 3 texcoord output registers not supported')),
    'oFog': lambda: (_ for _ in ()).throw(Exception('Fog output register not supported')),
    'oPts': lambda: (_ for _ in ()).throw(Exception('Point size output register not supported')),
}

_possibleoutputs = (list(_outputstoname.keys()) + list(_invalidoutputs.keys()))

def _negate(operand: str) -> str:
    return operand.replace('-', '') if '-' in operand else '-' + operand

def _parse_version(line):
    if line not in ['vs_1_0', 'vs_1_1', 'vs_1_2', 'vs_2_0', 'vs_2_1', 'vs_2_x', 'vs_3_0']:
        raise Exception(f'Only vs_3_0 or lower is supported, got {line}')
    else: 
        return [_comment('Vertex Shader generated by dxbc2pica 0.0.1'), _comment(f'd3d version: {line}'), _comment()]

def _parsebreak(opcode, operands) -> list[str]:
    if len(opcode) == 1:
        return [f'{opcode[0]}\n']
    else:
        return [f'cmp {operands[0]}, {opcode[1]}, {opcode[1]}, {operands[1]}\n', 'breakc cmp.x\n']

def _parsedcl(opcode, operands) -> list[str]: 
    if operands[0] in ['2d', 'cube', 'volume', '3d']: # texture samplers
        raise Exception("Texture samplers not supported")
    
    # output reg or input reg?
    outopcode = '.out -' if ('o' in operands[0]) else '.in'

    if opcode[1] == 'texcoord': # force there to be a number
        return [f'{outopcode} {opcode[1]}0 {operands[0]}{output.ignoretab()}\n']
    return [f'{outopcode} {opcode[1]} {operands[0]}{output.ignoretab()}\n']

def _type1(opcode, operands) -> list[str]:
    if 'c' in operands[1] and 'c' in operands[2]:
        return [
            f'mov {operands[0]}, {operands[1]}\n',
            f'{opcode[0]} {operands[0]}, {operands[2]}, {operands[0]}\n'
        ]
    else:
        if 'c' in operands[2]:
            return [f'{opcode[0]} {operands[0]}, {operands[2]}, {operands[1]}\n']
        return [f'{opcode[0]} {operands[0]}, {operands[1]}, {operands[2]}\n']
        
def _type1i(opcode, operands) -> list[str]:
    if 'c' in operands[1] and 'c' in operands[2]:
        return [
            f'mov {operands[0]}, {operands[1]}\n',
            f'{opcode[0]} {operands[0]}, {_negate(operands[2])}, {_negate(operands[0])}\n'
        ]
    else:
        return [f'{opcode[0]} {operands[0]}, {operands[1]}, {operands[2]}\n']

def _type1u(opcode, operands) -> list[str]:
    return [f'{opcode[0]} {operands[0]}, {operands[1]}\n']

def _parseif(opcode, operands) -> list[str]:
    if len(opcode) == 1: 
        if 'p' in operands[0]: return [f'ifc {operands[0].replace('p0', 'cmp')}\n']
        else: return [f'ifu {operands[0]}\n']
    return [
        f'cmp {operands[0]}, {opcode[1]}, {opcode[1]}, {operands[1]}\n',
        'ifc cmp.x\n'
    ]
    
def _parsemad(opcode, operands) -> list[str]:
    numconstants = sum(['c' in op for op in operands])
    # if there are no constants or there is a uniform in either src2 or src3 do nothing
    if sum(['c' in op for op in operands]) == 0 or (numconstants == 1 and 'c' not in operands[1]): return [f'mad {operands[0]}, {operands[1]}, {operands[2]}, {operands[3]}\n']
    return _instr['mul'](['mul'], operands) + _instr['add'](['add'], [operands[0], operands[0], operands[3]])

def _parsesetp(opcode, operands) -> list[str]:
    return [_comment(f'{opcode} {operands}')]
    
def _setoutputused(output: str) -> bool:
    if output in _invalidoutputs: 
        _invalidoutputs[output]()
    used = _outputsused[output]
    _outputsused[output] = True
    return used

# yet to implement:
# lit - vs
# m3x2 - vs (generally unused, low prio)
# m3x3 - vs (generally unused, low prio)
# m3x4 - vs (generally unused, low prio)
# m4x3 - vs (generally unused, low prio)
# m4x4 - vs (generally unused, low prio)
# pow - vs
# setp_comp - vs
# sincos - vs (inadvisable to use, low prio)

_instr: dict[str, Callable[[list[str], list[str]], list[str]]] = {
    'abs': lambda opcode, operands: [f'max {operands[0]}, {operands[1]}, {_negate(operands[1])}\n'],
    'add': _type1,
    'break': _parsebreak,
    'breakp': lambda opcode, operands: [f'breakc {operands[0].replace('p0', 'cmp')}\n'],
    'call': lambda opcode, operands: [f'call {operands[0]}\n'],
    'callnz': lambda opcode, operands: [f'call{'u' if 'b' in operands[1] else 'c'} {operands[1].replace('p0', 'cmp')}, {operands[0]}\n'],
    'crs': lambda opcode, operands: (_ for _ in ()).throw(Exception('crs not supported, make sure your compiler is set not to keep macros')),
    'dcl': _parsedcl,
    'def': lambda opcode, operands: [f'.constf {operands[0]}({operands[1]}, {operands[2]}, {operands[3]}, {operands[4]}{output.ignoretab()})\n'],
    'defb': lambda opcode, operands: (_ for _ in ()).throw(Exception('defb not supported')),
    'defi': lambda opcode, operands: [f'.consti {operands[0]}({operands[1]}, {operands[2]}, {operands[3]}, {operands[4]}){output.ignoretab()}\n'],
    'dp3': _type1,
    'dp4': _type1,
    'dst': _type1i,
    'else': lambda opcode, operands: ['.else\n'],
    'endif': lambda opcode, operands: [f'.end{output.dectab()}\n'],
    'endloop': lambda opcode, operands: [f'.end{output.dectab()}\n'],
    'endrep': lambda opcode, operands: [f'.end{output.dectab()}\n'],
    'exp': lambda opcode, operands: [f'ex2 {operands[0]}, {operands[1]}\n'],
    'expp': lambda opcode, operands: [f'ex2 {operands[0]}, {operands[1]}\n'],
    'frc': lambda opcode, operands: _type1u(['flr'], operands) + _instr['sub'](['sub'], [operands[0], operands[1], operands[0]]),
    'if': _parseif,
    'label': lambda opcode, operands: [f' {operands[0]}\n'],
    # 'lit': lambda opcode, operands: f'max {operands[0]}.x, {operands[1]}\n',
    'log': lambda opcode, operands: _type1u(['lg2'], operands),
    'logp': lambda opcode, operands: _type1u(['lg2'], operands),
    'loop': lambda opcode, operands: [f'for {operands[1]}\n'],
    'lrp': lambda opcode, operands: _instr['sub'](['sub'], [operands[0], operands[2], operands[3]]) + _instr['mul'](['mul'], [operands[0], operands[1], operands[0]]) + _instr['add'](['add'], [operands[0], operands[0], operands[3]]),
    'mad': _parsemad,
    'max': _type1,
    'min': _type1,
    # required because in vs_1_1 the mova instruction doesn't exist
    'mov': lambda opcode, operands: _type1u(opcode, operands) if 'a0' not in operands[0] else _instr['mova'](['mova'], operands),
    'mova': _type1u,
    'mul': _type1,
    'nop': lambda opcode, operands: ['nop\n'],
    'nrm': lambda opcode, operands: _instr['dp4'](['dp4'], [operands[0], operands[1], operands[1]]) + _instr['rsq'](['rsq'], [operands[0], operands[0]]) + _instr['mul'](['mul'], [operands[0], operands[1], operands[0]]),
    # from Microsoft's documentation
    'pow': lambda opcode, operands: _instr['abs'](['abs'], [operands[0], operands[1]]) + _instr['log'](['log'], [operands[0], operands[0]]) + _instr['mul'](['mul'], [operands[0], operands[2], operands[0]]) + _instr['exp'](['exp'], [operands[0], operands[0]]),
    'rcp': _type1u,
    'rep': lambda opcode, operands: [f'for {operands[0]}{output.inctab_after()}\n'],
    'ret': lambda opcode, operands: ['jmp'], # incomplete instruction, must be followed by a label
    'rsq': _type1u,
    'setp': _parsesetp,
    'sge': _type1i,
    #TODO: use 4 instruction version in case of uniform instead of the autogenerated 5 using movs
    'sgn': lambda opcode, operands: _instr['slt'](['slt'], [operands[2], _negate(operands[1]), operands[1]]) + _instr['slt'](['slt'], [operands[3], operands[1], _negate(operands[1])]) + _instr['sub'](['sub'], [operands[0], operands[2], operands[3]]),
    'sincos': lambda opcode, operands: (_ for _ in ()).throw(Exception('sincos not supported')),
    'slt': _type1i,
    'sub': lambda opcode, operands: _instr['add'](['add'], [operands[0], operands[1], _negate(operands[2])]),
    'texldl': lambda opcode, operands: (_ for _ in ()).throw(Exception('texldl not supported')),
    'vs': lambda opcode, operands: [_comment(f'version {operands[0]}')],
}