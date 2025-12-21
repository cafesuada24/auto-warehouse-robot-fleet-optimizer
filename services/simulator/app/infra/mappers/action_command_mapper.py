# Copyright (C) 2025 Cafesuada - All Rights Reserved
#
# This source code is protected under international copyright law.  All rights
# reserved and protected by the copyright holders.
# This file is confidential and only available to authorized individuals with the
# permission of the copyright holders.  If you encounter this file and do not have
# permission, please contact the copyright holders and delete this file.

from awrfo.contracts.commands.v1.action_command_pb2 import ActionCommand, CommandType

from app.types import IDType
from app.world.models.command import (
    AssignTaskCommand,
    CancelTaskCommand,
    CommandBase,
    MoveToCommand,
)


def proto_to_command(action_command: ActionCommand) -> CommandBase:
    """Convert an ActionCommand proto to a specific command that is executable by the simulator."""
    if action_command.type == CommandType.COMMAND_TYPE_ASSIGN_TASK:
        if not action_command.HasField('assign_task'):
            raise ValueError(
                'Invalid action command: action type is AssignTask but the respective field is empty.',
            )
        return AssignTaskCommand(
            id=IDType(action_command.id),
            task_id=IDType(action_command.assign_task.task_id),
            robot_id=IDType(action_command.robot_id),
            issued_at_ms=0,
        )

    if action_command.type == CommandType.COMMAND_TYPE_MOVE_TO:
        if not action_command.HasField('move_to'):
            raise ValueError(
                'Invalid action command: action type is MoveTo but the respective field is empty.',
            )

        return MoveToCommand(
            id=IDType(action_command.id),
            robot_id=IDType(action_command.robot_id),
            pos=(action_command.move_to.target.x, action_command.move_to.target.y),
            arrive_eps=action_command.move_to.arrive_eps
            if action_command.move_to.HasField('arrive_eps')
            else 0.1,
            issued_at_ms=0,
        )

    if action_command.type == CommandType.COMMAND_TYPE_CANCEL_TASK:
        if not action_command.HasField('cancel_task'):
            raise ValueError(
                'Invalid action command: action type is CancelTask but the respective field is empty.',
            )

        return CancelTaskCommand(
            id=IDType(action_command.id),
            robot_id=IDType(action_command.robot_id),
            task_id=IDType(action_command.cancel_task.task_id),
            issued_at_ms=0,
        )


    raise ValueError(f'Unsupported ActionCommand payload: {action_command}')


def serialized_proto_to_command(serialized: bytes) -> CommandBase:
    """Convert an serialized ActionCommand proto to a specific command that is executable by the simulator."""
    ac = ActionCommand().FromString(serialized)
    return proto_to_command(ac)
