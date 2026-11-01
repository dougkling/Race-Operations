"""Stage a narrow patch to the installed RaceBot; preserve all other application code."""
import argparse
import ast
from pathlib import Path

INIT = """    # Race Operations AI recovery v1
    from ai_recovery import AIRecovery
    ai_recovery = AIRecovery(hub, lambda key, model: OpenAI(key, model).post(
        'responses', {'model': model, 'input': 'Reply with OK.',
                      'max_output_tokens': 64, 'store': False}), load_key)
"""
GET = """            if self.path == '/api/ops/ai':
                if self.client_address[0] not in ('127.0.0.1', '::1'):
                    return self.respond(403, {'error': 'Local operation only'})
                return self.respond(200, dict(ai_recovery.snapshot(), token=csrf))
"""
POST = """                if self.path == '/api/ops/ai/reconnect':
                    if self.client_address[0] not in ('127.0.0.1', '::1'):
                        return self.respond(403, {'error': 'Local operation only'})
                    return self.respond(202, ai_recovery.start(data.get('requestId')))
"""


def patch(source):
    ast.parse(source)
    if '# Race Operations AI recovery v1' in source:
        if all(block in source for block in (INIT, GET, POST)):
            return source
        raise ValueError('Existing AI patch differs; refusing an ambiguous update.')
    # This POST route remains behind the existing Host and X-PitWall-Token checks.
    guard = "if not self.allowed_host() or self.headers.get('X-PitWall-Token') != csrf:"
    anchors = [('    csrf = secrets.token_urlsafe(32)\n', INIT, False),
               ("            if self.path == '/api/state':\n", GET, True),
               ("                if self.path == '/api/simulate':\n", POST, True)]
    if source.count(guard) != 1:
        raise ValueError('RaceBot request protection was not recognized.')
    for anchor, block, before in anchors:
        if source.count(anchor) != 1:
            raise ValueError('Installed RaceBot layout differs; no files changed.')
        source = source.replace(anchor, block+anchor if before else anchor+block, 1)
    compile(source, 'app.py', 'exec')
    return source


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('output')
    args = parser.parse_args()
    result = patch(Path(args.source).read_text(encoding='utf-8-sig'))
    Path(args.output).write_text(result, encoding='utf-8')
