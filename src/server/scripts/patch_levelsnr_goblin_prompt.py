#!/usr/bin/env python3
"""
Patch LevelsNR.swf to reduce the GoblinRiver room-5 parrot fallback delay.

This performs a narrow ABC bytecode patch in a_Room_NRIMR03.WaitingOnGoblin:
the AtTime(12000) fallback becomes AtTime(2500).

The patch is transactional and keeps SWF assets intact because it does not
recompile or re-import symbols.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Sequence, Tuple


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SERVER_TAPES = os.path.join(ROOT, "server_tapes")
if SERVER_TAPES not in sys.path:
    sys.path.insert(0, SERVER_TAPES)

from patch_swf_devflags import (  # type: ignore
    BytePatch,
    PatchError,
    apply_patches,
    class_index_by_name,
    disassemble,
    ensure_backup,
    method_idx_for_trait,
    parse_abc,
    parse_swf,
    u30_operand_name,
    write_swf,
    write_u30,
)


DEFAULT_SWF_PATH = os.path.join(
    ROOT, "src", "client", "content", "localhost", "p", "cbp", "LevelsNR.swf"
)
CLASS_NAME = "a_Room_NRIMR03"
METHOD_NAME = "WaitingOnGoblin"
OLD_DELAY_MS = 12000
NEW_DELAY_MS = 2500


def analyze_patch(swf_path: str, body: bytearray):
    ctx = parse_swf(swf_path)
    abc = parse_abc(ctx)

    class_index = class_index_by_name(abc, CLASS_NAME)
    if class_index is None:
        raise PatchError(f"{CLASS_NAME} class not found")

    method_idx = method_idx_for_trait(abc.instances[class_index].traits, abc, METHOD_NAME)
    if method_idx is None:
        raise PatchError(f"{CLASS_NAME}.{METHOD_NAME} not found")

    mbody = abc.method_bodies.get(method_idx)
    if mbody is None:
        raise PatchError(f"{CLASS_NAME}.{METHOD_NAME} body not found")

    code = bytes(body[mbody.code_start : mbody.code_start + mbody.code_len])
    instrs = disassemble(code, f"{CLASS_NAME}.{METHOD_NAME}")

    candidates: List[Tuple[int, int]] = []
    for i, inst in enumerate(instrs):
        if inst.opcode != 0x25:
            continue
        if not inst.operands or inst.operands[0][0] != "u30" or inst.operands[0][1] != OLD_DELAY_MS:
            continue
        for j in range(i + 1, min(i + 4, len(instrs))):
            lookahead = instrs[j]
            if lookahead.opcode == 0x46 and u30_operand_name(lookahead, abc.multiname_names) == "AtTime":
                candidates.append((inst.offset, inst.size))
                break

    if not candidates:
        raise PatchError(
            f"Could not find pushshort {OLD_DELAY_MS} used by {CLASS_NAME}.{METHOD_NAME}.AtTime"
        )
    if len(candidates) > 1:
        raise PatchError(
            f"Found multiple candidate delays for {CLASS_NAME}.{METHOD_NAME}: {candidates}"
        )

    inst_offset, inst_size = candidates[0]
    operand_start = mbody.code_start + inst_offset + 1
    operand_end = mbody.code_start + inst_offset + inst_size
    current_bytes = bytes(body[operand_start:operand_end])
    replacement = write_u30(NEW_DELAY_MS)
    if current_bytes == replacement:
        return ctx, []
    if len(current_bytes) != len(replacement):
        raise PatchError(
            f"Unsupported varint width change for delay: {len(current_bytes)} -> {len(replacement)}"
        )

    return ctx, [
        BytePatch(
            key="levelsnr_goblin_prompt_delay",
            start=operand_start,
            end=operand_end,
            data=replacement,
            detail=f"Change {CLASS_NAME}.{METHOD_NAME} AtTime({OLD_DELAY_MS}) to AtTime({NEW_DELAY_MS})",
        )
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch LevelsNR.swf GoblinRiver prompt delay")
    parser.add_argument("--swf-path", default=DEFAULT_SWF_PATH, help="Target SWF path")
    parser.add_argument("--verify", action="store_true", help="Inspect only, do not write")
    parser.add_argument("--dry-run", action="store_true", help="Inspect only, do not write")
    args = parser.parse_args()

    swf_path = os.path.abspath(args.swf_path)

    try:
        ctx = parse_swf(swf_path)
        body_mut = bytearray(ctx.body)
        abc = parse_abc(ctx)

        class_index = class_index_by_name(abc, CLASS_NAME)
        if class_index is None:
            raise PatchError(f"{CLASS_NAME} class not found")
        method_idx = method_idx_for_trait(abc.instances[class_index].traits, abc, METHOD_NAME)
        if method_idx is None:
            raise PatchError(f"{CLASS_NAME}.{METHOD_NAME} not found")
        mbody = abc.method_bodies.get(method_idx)
        if mbody is None:
            raise PatchError(f"{CLASS_NAME}.{METHOD_NAME} body not found")
        code = bytes(body_mut[mbody.code_start : mbody.code_start + mbody.code_len])
        instrs = disassemble(code, f"{CLASS_NAME}.{METHOD_NAME}")

        patch_candidates: List[Tuple[int, int, int]] = []
        for i, inst in enumerate(instrs):
            if inst.opcode != 0x25:
                continue
            if not inst.operands or inst.operands[0][0] != "u30":
                continue
            delay_value = inst.operands[0][1]
            if delay_value not in (OLD_DELAY_MS, NEW_DELAY_MS):
                continue
            for j in range(i + 1, min(i + 4, len(instrs))):
                lookahead = instrs[j]
                if lookahead.opcode == 0x46 and u30_operand_name(lookahead, abc.multiname_names) == "AtTime":
                    patch_candidates.append((inst.offset, inst.size, delay_value))
                    break

        if not patch_candidates:
            raise PatchError(
                f"Could not find AtTime delay used by {CLASS_NAME}.{METHOD_NAME}"
            )
        if len(patch_candidates) > 1:
            raise PatchError(
                f"Found multiple candidate delays for {CLASS_NAME}.{METHOD_NAME}: {patch_candidates}"
            )

        inst_offset, inst_size, current_delay = patch_candidates[0]
        operand_start = mbody.code_start + inst_offset + 1
        operand_end = mbody.code_start + inst_offset + inst_size
        current_bytes = bytes(body_mut[operand_start:operand_end])
        replacement = write_u30(NEW_DELAY_MS)

        print(f"SWF: {swf_path}")
        print(f"Target: {CLASS_NAME}.{METHOD_NAME}")
        print(f"Current delay bytes: {current_bytes.hex()} ({current_delay})")
        print(f"Replacement bytes:   {replacement.hex()} ({NEW_DELAY_MS})")

        if current_bytes == replacement:
            print("No changes needed.")
            return 0
        if len(current_bytes) != len(replacement):
            raise PatchError(
                f"Unsupported varint width change for delay: {len(current_bytes)} -> {len(replacement)}"
            )

        patch = BytePatch(
            key="levelsnr_goblin_prompt_delay",
            start=operand_start,
            end=operand_end,
            data=replacement,
            detail=f"Change {CLASS_NAME}.{METHOD_NAME} AtTime({OLD_DELAY_MS}) to AtTime({NEW_DELAY_MS})",
        )

        print(f"Patch: {patch.detail}")
        if args.verify or args.dry_run:
            return 0

        ensure_backup(swf_path)
        delta = apply_patches(body_mut, [patch])
        write_swf(ctx, body_mut, delta)
        print("Patch apply complete.")
        return 0
    except PatchError as exc:
        print(f"Patch error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
