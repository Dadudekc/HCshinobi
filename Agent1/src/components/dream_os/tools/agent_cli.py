"""
Agent CLI Interface for Dream.OS

This module provides a command-line interface for agents to interact with
the agent communication system.
"""

import asyncio
import argparse
import json
from typing import Optional
from pathlib import Path

from ..core.src.services.agent_communication import AgentCommunication

class AgentCLI:
    """Command-line interface for agent communication."""
    
    def __init__(self, agent_id: str):
        """
        Initialize the agent CLI.
        
        Args:
            agent_id: Unique identifier for this agent
        """
        self.agent_id = agent_id
        self.comm = AgentCommunication(agent_id)
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser."""
        parser = argparse.ArgumentParser(description='Agent Communication CLI')
        subparsers = parser.add_subparsers(dest='command', help='Command to execute')
        
        # Message commands
        msg_parser = subparsers.add_parser('message', help='Message operations')
        msg_subparsers = msg_parser.add_subparsers(dest='msg_command')
        
        send_parser = msg_subparsers.add_parser('send', help='Send a message')
        send_parser.add_argument('recipient', help='Recipient agent ID')
        send_parser.add_argument('type', help='Message type')
        send_parser.add_argument('content', help='Message content')
        
        check_parser = msg_subparsers.add_parser('check', help='Check messages')
        
        # State commands
        state_parser = subparsers.add_parser('state', help='State operations')
        state_subparsers = state_parser.add_subparsers(dest='state_command')
        
        update_parser = state_subparsers.add_parser('update', help='Update state')
        update_parser.add_argument('key', help='State key')
        update_parser.add_argument('value', help='State value')
        
        get_parser = state_subparsers.add_parser('get', help='Get state')
        get_parser.add_argument('--key', help='Specific key to get')
        
        # Status commands
        status_parser = subparsers.add_parser('status', help='Status operations')
        status_subparsers = status_parser.add_subparsers(dest='status_command')
        
        update_status_parser = status_subparsers.add_parser('update', help='Update status')
        update_status_parser.add_argument('status', help='Status JSON')
        
        get_status_parser = status_subparsers.add_parser('get', help='Get status')
        get_status_parser.add_argument('--agent', help='Specific agent ID')
        
        # Task commands
        task_parser = subparsers.add_parser('task', help='Task operations')
        task_subparsers = task_parser.add_subparsers(dest='task_command')
        
        coord_parser = task_subparsers.add_parser('coordinate', help='Coordinate task')
        coord_parser.add_argument('task_id', help='Task ID')
        coord_parser.add_argument('action', help='Action to take')
        coord_parser.add_argument('data', help='Task data JSON')
        
        status_parser = task_subparsers.add_parser('status', help='Get task status')
        status_parser.add_argument('task_id', help='Task ID')
        
        # Cleanup command
        cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup old data')
        cleanup_parser.add_argument('--days', type=int, default=7, help='Days to keep')
        
        return parser
    
    async def run(self, args: Optional[list] = None):
        """
        Run the CLI.
        
        Args:
            args: Optional command-line arguments
        """
        parsed_args = self.parser.parse_args(args)
        
        if parsed_args.command == 'message':
            if parsed_args.msg_command == 'send':
                await self.comm.send_message(
                    parsed_args.recipient,
                    parsed_args.type,
                    json.loads(parsed_args.content)
                )
                print(f"Message sent to {parsed_args.recipient}")
            elif parsed_args.msg_command == 'check':
                messages = await self.comm.check_messages()
                print(json.dumps(messages, indent=2))
        
        elif parsed_args.command == 'state':
            if parsed_args.state_command == 'update':
                await self.comm.update_shared_state(
                    parsed_args.key,
                    json.loads(parsed_args.value)
                )
                print(f"State updated: {parsed_args.key}")
            elif parsed_args.state_command == 'get':
                state = await self.comm.get_shared_state(parsed_args.key)
                print(json.dumps(state, indent=2))
        
        elif parsed_args.command == 'status':
            if parsed_args.status_command == 'update':
                await self.comm.update_status(json.loads(parsed_args.status))
                print("Status updated")
            elif parsed_args.status_command == 'get':
                status = await self.comm.get_agent_status(parsed_args.agent)
                print(json.dumps(status, indent=2))
        
        elif parsed_args.command == 'task':
            if parsed_args.task_command == 'coordinate':
                await self.comm.coordinate_task(
                    parsed_args.task_id,
                    parsed_args.action,
                    json.loads(parsed_args.data)
                )
                print(f"Task coordinated: {parsed_args.task_id}")
            elif parsed_args.task_command == 'status':
                status = await self.comm.get_task_status(parsed_args.task_id)
                print(json.dumps(status, indent=2))
        
        elif parsed_args.command == 'cleanup':
            await self.comm.cleanup_old_data(parsed_args.days)
            print(f"Cleaned up data older than {parsed_args.days} days")

def main():
    """Main entry point for the agent CLI."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: agent_cli.py <agent_id> [command]")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    cli = AgentCLI(agent_id)
    
    asyncio.run(cli.run(sys.argv[2:]))

if __name__ == '__main__':
    main() 