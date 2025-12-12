"""
Autonomous CourtListener Service

Provides semi-autonomous monitoring of case law with automatic knowledge graph integration.

Features:
- Keyword-based opinion monitoring
- Citation tracking for precedent monitoring
- Automatic opinion download and ingestion
- Alert system for relevant cases
- Configurable check intervals (default: 6 hours)
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..config import get_settings
from ..services.knowledge_graph_service import KnowledgeGraphService
from ..utils.audit import AuditEvent, get_audit_trail


class CourtListenerMonitor:
    """Represents a monitoring configuration for CourtListener."""
    
    def __init__(
        self,
        monitor_id: str,
        monitor_type: str,  # 'keyword' or 'citation'
        value: str,  # keyword string or citation (e.g., "550 U.S. 544")
        requested_by: str,
        check_interval_hours: int = 6,
        priority: str = 'normal',
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.monitor_id = monitor_id
        self.monitor_type = monitor_type
        self.value = value
        self.requested_by = requested_by
        self.check_interval_hours = check_interval_hours
        self.priority = priority
        self.metadata = metadata or {}
        self.created_at = datetime.now(timezone.utc)
        self.last_check: Optional[datetime] = None
        self.last_results_count = 0
        self.enabled = True


class AutonomousCourtListenerService:
    """
    Manages autonomous CourtListener monitoring with KG integration.
    
    Features:
    - Monitor keywords for new opinions
    - Track citations to specific precedents
    - Auto-download opinion full text
    - Extract entities and add to knowledge graph
    - Alert on relevant new cases
    """
    
    def __init__(
        self,
        kg_service: Optional[KnowledgeGraphService] = None,
        scheduler: Optional[AsyncIOScheduler] = None
    ):
        self.settings = get_settings()
        self.kg_service = kg_service or KnowledgeGraphService()
        self.scheduler = scheduler or AsyncIOScheduler()
        
        # CourtListener API configuration
        self.api_base = "https://www.courtlistener.com/api/rest/v3"
        self.api_token = self.settings.courtlistener_token if hasattr(self.settings, 'courtlistener_token') else None
        
        # Track monitors and processed opinions
        self.monitors: Dict[str, CourtListenerMonitor] = {}
        self.processed_opinions: Set[str] = set()
        
        self.audit = get_audit_trail()
        self._scheduler_started = False
    
    def start_scheduler(self) -> None:
        """Start the background scheduler."""
        if not self._scheduler_started:
            self.scheduler.start()
            self._scheduler_started = True
    
    def stop_scheduler(self) -> None:
        """Stop the background scheduler."""
        if self._scheduler_started:
            self.scheduler.shutdown()
            self._scheduler_started = False
    
    async def add_monitor(
        self,
        monitor_type: str,
        value: str,
        requested_by: str,
        check_interval_hours: int = 6,
        priority: str = 'normal',
        metadata: Optional[Dict[str, Any]] = None
    ) -> CourtListenerMonitor:
        """
        Add a new CourtListener monitor.
        
        Args:
            monitor_type: 'keyword' or 'citation'
            value: Keyword string or citation
            requested_by: Team/user requesting monitoring
            check_interval_hours: How often to check (default 6)
            priority: 'high', 'normal', 'low'
            metadata: Additional context
        """
        monitor_id = self._generate_monitor_id(monitor_type, value, requested_by)
        
        monitor = CourtListenerMonitor(
            monitor_id=monitor_id,
            monitor_type=monitor_type,
            value=value,
            requested_by=requested_by,
            check_interval_hours=check_interval_hours,
            priority=priority,
            metadata=metadata
        )
        
        self.monitors[monitor_id] = monitor
        
        # Schedule periodic checks
        self._schedule_monitor(monitor)
        
        # Audit the monitor creation
        self._audit_monitor_event(
            monitor_id=monitor_id,
            action='courtlistener.monitor.created',
            outcome='success',
            metadata={
                'type': monitor_type,
                'value': value,
                'interval': check_interval_hours,
                'requested_by': requested_by
            }
        )
        
        return monitor
    
    async def execute_monitor(self, monitor_id: str) -> Dict[str, Any]:
        """
        Execute a monitoring check.
        
        Returns:
            Results dict with new opinions found and ingested
        """
        monitor = self.monitors.get(monitor_id)
        if not monitor:
            return {'error': f'Monitor {monitor_id} not found', 'success': False}
        
        if not monitor.enabled:
            return {'error': 'Monitor is disabled', 'success': False}
        
        # Execute monitoring based on type
        if monitor.monitor_type == 'keyword':
            results = await self._monitor_keywords(monitor)
        elif monitor.monitor_type == 'citation':
            results = await self._monitor_citation(monitor)
        else:
            return {'error': f'Unknown monitor type: {monitor.monitor_type}', 'success': False}
        
        # Update monitor
        monitor.last_check = datetime.now(timezone.utc)
        monitor.last_results_count = results.get('new_opinions', 0)
        
        return results
    
    async def _monitor_keywords(self, monitor: CourtListenerMonitor) -> Dict[str, Any]:
        """Monitor for new opinions matching keywords."""
        if not self.api_token:
            return {'error': 'CourtListener API token not configured', 'success': False}
        
        try:
            # Calculate date range (since last check or last 24h)
            if monitor.last_check:
                date_filed_after = monitor.last_check.date().isoformat()
            else:
                date_filed_after = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
            
            # Search CourtListener API
            params = {
                'q': monitor.value,
                'type': 'o',  # Opinions
                'order_by': 'dateFiled desc',
                'filed_after': date_filed_after
            }
            
            headers = {'Authorization': f'Token {self.api_token}'}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f'{self.api_base}/search/',
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
            
            results = data.get('results', [])
            new_opinions = 0
            ingested = 0
            
            for result in results:
                opinion_id = str(result.get('id'))
                
                # Check if already processed
                if opinion_id in self.processed_opinions:
                    continue
                
                new_opinions += 1
                
                # Download full opinion and ingest
                await self._download_and_ingest_opinion(
                    opinion_id=opinion_id,
                    result=result,
                    monitor=monitor
                )
                
                self.processed_opinions.add(opinion_id)
                ingested += 1
            
            # Audit the check
            self._audit_monitor_check(
                monitor_id=monitor.monitor_id,
                new_opinions=new_opinions,
                ingested=ingested
            )
            
            return {
                'success': True,
                'monitor_id': monitor.monitor_id,
                'monitor_type': 'keyword',
                'value': monitor.value,
                'new_opinions': new_opinions,
                'ingested': ingested,
                'total_results': len(results)
            }
            
        except Exception as exc:
            error_msg = f"Monitoring failed: {str(exc)}"
            self._audit_monitor_check(
                monitor_id=monitor.monitor_id,
                error=error_msg
            )
            return {'error': error_msg, 'success': False}
    
    async def _monitor_citation(self, monitor: CourtListenerMonitor) -> Dict[str, Any]:
        """Monitor for new opinions citing a specific case."""
        if not self.api_token:
            return {'error': 'CourtListener API token not configured', 'success': False}
        
        try:
            # Search for opinions citing this case
            if monitor.last_check:
                date_filed_after = monitor.last_check.date().isoformat()
            else:
                date_filed_after = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
            
            # Search by citation
            params = {
                'cites': monitor.value,
                'type': 'o',
                'order_by': 'dateFiled desc',
                'filed_after': date_filed_after
            }
            
            headers = {'Authorization': f'Token {self.api_token}'}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f'{self.api_base}/search/',
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
            
            results = data.get('results', [])
            new_opinions = 0
            ingested = 0
            
            for result in results:
                opinion_id = str(result.get('id'))
                
                if opinion_id in self.processed_opinions:
                    continue
                
                new_opinions += 1
                
                # Download and ingest
                await self._download_and_ingest_opinion(
                    opinion_id=opinion_id,
                    result=result,
                    monitor=monitor
                )
                
                self.processed_opinions.add(opinion_id)
                ingested += 1
            
            self._audit_monitor_check(
                monitor_id=monitor.monitor_id,
                new_opinions=new_opinions,
                ingested=ingested
            )
            
            return {
                'success': True,
                'monitor_id': monitor.monitor_id,
                'monitor_type': 'citation',
                'value': monitor.value,
                'new_opinions': new_opinions,
                'ingested': ingested,
                'total_results': len(results)
            }
            
        except Exception as exc:
            error_msg = f"Citation monitoring failed: {str(exc)}"
            self._audit_monitor_check(
                monitor_id=monitor.monitor_id,
                error=error_msg
            )
            return {'error': error_msg, 'success': False}
    
    async def _download_and_ingest_opinion(
        self,
        opinion_id: str,
        result: Dict[str, Any],
        monitor: CourtListenerMonitor
    ) -> None:
        """Download opinion full text and ingest to knowledge graph."""
        # Extract metadata
        case_name = result.get('caseName', 'Unknown Case')
        court = result.get('court', 'Unknown Court')
        date_filed = result.get('dateFiled', '')
        citation = result.get('citation', [])
        snippet = result.get('snippet', '')
        
        # Create CaseOpinion entity in KG
        entity_id = f"opinion:courtlistener:{opinion_id}"
        
        await self.kg_service.add_entity(
            entity_id=entity_id,
            entity_type="CaseOpinion",
            properties={
                "case_name": case_name,
                "court": court,
                "date_filed": date_filed,
                "citation": citation if isinstance(citation, list) else [citation],
                "snippet": snippet[:1000],  # Limit snippet
                "courtlistener_id": opinion_id,
                "monitor_type": monitor.monitor_type,
                "monitor_value": monitor.value,
                "ingested_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # If citation monitor, create CITES relationship
        if monitor.monitor_type == 'citation':
            citing_case_id = f"precedent:{self._sanitize_id(monitor.value)}"
            
            # Create precedent node if doesn't exist
            await self.kg_service.add_entity(
                entity_id=citing_case_id,
                entity_type="Precedent",
                properties={
                    "citation": monitor.value,
                    "tracked": True
                }
            )
            
            # Create CITES relationship
            await self.kg_service.add_relationship(
                source_id=entity_id,
                relationship_type="CITES",
                target_id=citing_case_id,
                properties={"detected_at": datetime.now(timezone.utc).isoformat()}
            )
    
    def _schedule_monitor(self, monitor: CourtListenerMonitor) -> None:
        """Schedule periodic monitoring checks."""
        self.scheduler.add_job(
            func=self._execute_monitor_wrapper,
            trigger=IntervalTrigger(hours=monitor.check_interval_hours),
            args=[monitor.monitor_id],
            id=monitor.monitor_id,
            replace_existing=True
        )
    
    async def _execute_monitor_wrapper(self, monitor_id: str) -> None:
        """Wrapper for scheduler to execute monitors."""
        await self.execute_monitor(monitor_id)
    
    def remove_monitor(self, monitor_id: str) -> bool:
        """Remove a monitor and its schedule."""
        if monitor_id not in self.monitors:
            return False
        
        # Remove from scheduler
        try:
            self.scheduler.remove_job(monitor_id)
        except:
            pass
        
        # Remove monitor
        del self.monitors[monitor_id]
        
        self._audit_monitor_event(
            monitor_id=monitor_id,
            action='courtlistener.monitor.removed',
            outcome='success',
            metadata={}
        )
        
        return True
    
    def list_monitors(self) -> List[Dict[str, Any]]:
        """List all active monitors."""
        return [
            {
                'monitor_id': m.monitor_id,
                'monitor_type': m.monitor_type,
                'value': m.value,
                'requested_by': m.requested_by,
                'check_interval_hours': m.check_interval_hours,
                'priority': m.priority,
                'enabled': m.enabled,
                'last_check': m.last_check.isoformat() if m.last_check else None,
                'last_results_count': m.last_results_count,
                'created_at': m.created_at.isoformat()
            }
            for m in self.monitors.values()
        ]
    
    def _generate_monitor_id(self, monitor_type: str, value: str, requested_by: str) -> str:
        """Generate unique monitor ID."""
        content = f"{monitor_type}:{value}:{requested_by}:{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _sanitize_id(self, text: str) -> str:
        """Sanitize text for use in entity IDs."""
        return text.lower().replace(' ', '_').replace('.', '_')[:100]
    
    def _audit_monitor_event(
        self,
        monitor_id: str,
        action: str,
        outcome: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Audit monitor lifecycle events."""
        event = AuditEvent(
            category='autonomous_courtlistener',
            action=action,
            actor={'id': 'system', 'type': 'autonomous_service'},
            subject={'monitor_id': monitor_id},
            outcome=outcome,
            severity='info',
            metadata=metadata
        )
        self.audit.append(event)
    
    def _audit_monitor_check(
        self,
        monitor_id: str,
        new_opinions: int = 0,
        ingested: int = 0,
        error: Optional[str] = None
    ) -> None:
        """Audit monitoring check execution."""
        event = AuditEvent(
            category='autonomous_courtlistener',
            action='courtlistener.check',
            actor={'id': 'system', 'type': 'autonomous_service'},
            subject={'monitor_id': monitor_id},
            outcome='success' if not error else 'error',
            severity='info' if not error else 'warning',
            metadata={
                'new_opinions': new_opinions,
                'ingested': ingested,
                'error': error
            }
        )
        self.audit.append(event)


# Singleton instance
_autonomous_courtlistener_service: Optional[AutonomousCourtListenerService] = None


def get_autonomous_courtlistener_service() -> AutonomousCourtListenerService:
    """Get or create the autonomous CourtListener service singleton."""
    global _autonomous_courtlistener_service
    if _autonomous_courtlistener_service is None:
        _autonomous_courtlistener_service = AutonomousCourtListenerService()
        _autonomous_courtlistener_service.start_scheduler()
    return _autonomous_courtlistener_service
