"""QA Oversight service for monitoring and analyzing agent behavior."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class LogReader:
    """Reads agent logs from the logging system."""
    
    def __init__(self, log_dir: Path | None = None):
        self.log_dir = log_dir or Path("logs")
        
    def read_logs(self, agent_name: str, time_frame: str) -> List[Dict[str, Any]]:
        """Read logs for a specific agent within a time frame.
        
        Args:
            agent_name: Name of the agent to read logs for
            time_frame: Time frame (e.g., "last_hour", "last_day")
            
        Returns:
            List of log entries
        """
        logs = []
        try:
            # Calculate time threshold
            now = datetime.now()
            if time_frame == "last_hour":
                threshold = now - timedelta(hours=1)
            elif time_frame == "last_day":
                threshold = now - timedelta(days=1)
            else:
                threshold = now - timedelta(hours=1)  # Default to last hour
            
            # Read from log files if they exist
            log_file = self.log_dir / f"{agent_name}.log"
            if log_file.exists():
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            entry_time = datetime.fromisoformat(entry.get('timestamp', ''))
                            if entry_time >= threshold:
                                logs.append(entry)
                        except (json.JSONDecodeError, ValueError):
                            # Skip malformed log entries
                            continue
        except Exception as e:
            logger.error(f"Error reading logs for {agent_name}: {e}")
            
        return logs


class TraceReader:
    """Reads agent execution traces."""
    
    def __init__(self, trace_dir: Path | None = None):
        self.trace_dir = trace_dir or Path("traces")
        
    def read_traces(self, agent_name: str, time_frame: str) -> List[Dict[str, Any]]:
        """Read execution traces for a specific agent.
        
        Args:
            agent_name: Name of the agent
            time_frame: Time frame for traces
            
        Returns:
            List of trace events
        """
        traces = []
        try:
            now = datetime.now()
            if time_frame == "last_hour":
                threshold = now - timedelta(hours=1)
            elif time_frame == "last_day":
                threshold = now - timedelta(days=1)
            else:
                threshold = now - timedelta(hours=1)
            
            trace_file = self.trace_dir / f"{agent_name}_traces.jsonl"
            if trace_file.exists():
                with open(trace_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            entry_time = datetime.fromisoformat(entry.get('timestamp', ''))
                            if entry_time >= threshold:
                                traces.append(entry)
                        except (json.JSONDecodeError, ValueError):
                            continue
        except Exception as e:
            logger.error(f"Error reading traces for {agent_name}: {e}")
            
        return traces


class AgentMemoryStore:
    """Manages agent memory state."""
    
    def __init__(self, memory_dir: Path | None = None):
        self.memory_dir = memory_dir or Path("memory")
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
    def get_memory(self, agent_name: str) -> Dict[str, Any]:
        """Retrieve current memory state for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent memory state
        """
        memory_file = self.memory_dir / f"{agent_name}_memory.json"
        
        if memory_file.exists():
            try:
                with open(memory_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error reading memory for {agent_name}: {e}")
                
        return {
            "agent_name": agent_name,
            "memory_content": {},
            "last_updated": datetime.now().isoformat(),
            "status": "no_memory_found"
        }
    
    def save_memory(self, agent_name: str, memory_data: Dict[str, Any]) -> None:
        """Save agent memory state.
        
        Args:
            agent_name: Name of the agent
            memory_data: Memory data to save
        """
        memory_file = self.memory_dir / f"{agent_name}_memory.json"
        try:
            with open(memory_file, 'w') as f:
                json.dump(memory_data, f, indent=2)
        except IOError as e:
            logger.error(f"Error saving memory for {agent_name}: {e}")


class QAOversightService:
    """Service for gathering and analyzing agent behavior data for QA oversight."""
    
    def __init__(
        self,
        log_dir: Path | None = None,
        trace_dir: Path | None = None,
        memory_dir: Path | None = None
    ):
        self.log_reader = LogReader(log_dir)
        self.trace_reader = TraceReader(trace_dir)
        self.memory_store = AgentMemoryStore(memory_dir)

    async def run_oversight_cycle(
        self,
        agent_names: List[str],
        time_frame: str = "last_hour"
    ) -> Dict[str, Any]:
        """Gather all relevant data for QA oversight analysis.
        
        Args:
            agent_names: List of agent names to gather data for
            time_frame: Time frame for data collection
            
        Returns:
            Dictionary containing logs, traces, and memory for all agents
        """
        oversight_data = {
            "logs": {},
            "traces": {},
            "memory": {},
            "metadata": {
                "collection_time": datetime.now().isoformat(),
                "time_frame": time_frame,
                "agent_count": len(agent_names)
            }
        }

        for agent_name in agent_names:
            try:
                oversight_data["logs"][agent_name] = self.log_reader.read_logs(
                    agent_name, time_frame
                )
                oversight_data["traces"][agent_name] = self.trace_reader.read_traces(
                    agent_name, time_frame
                )
                oversight_data["memory"][agent_name] = self.memory_store.get_memory(
                    agent_name
                )
            except Exception as e:
                logger.error(f"Error collecting oversight data for {agent_name}: {e}")
                oversight_data["logs"][agent_name] = []
                oversight_data["traces"][agent_name] = []
                oversight_data["memory"][agent_name] = {
                    "error": str(e),
                    "agent_name": agent_name
                }
        
        return oversight_data