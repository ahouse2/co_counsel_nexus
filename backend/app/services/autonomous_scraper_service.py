"""
Autonomous Web Scraper Service

Provides scheduled and on-demand web scraping with automatic knowledge graph integration.
Supports:
- Daily scraping for priority topics/theories
- On-demand triggers from strategy team or other teams
- Auto-ingestion of scraped content to knowledge graph
- Deduplication and intelligent scheduling
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from ..config import get_settings
from ..services.knowledge_graph_service import KnowledgeGraphService
from ..services.web_scrapers.california_codes_scraper import CaliforniaCodesScraper
from ..services.web_scrapers.ecfr_scraper import ECFRScraper
from ..utils.audit import AuditEvent, get_audit_trail


class ScrapingTrigger:
    """Represents a scraping trigger from a team or automated schedule."""
    
    def __init__(
        self,
        trigger_id: str,
        source: str,
        query: str,
        frequency: str,  # 'daily', 'on-demand'
        requested_by: str,  # Team name or 'system'
        priority: str = 'normal',  # 'high', 'normal', 'low'
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.trigger_id = trigger_id
        self.source = source
        self.query = query
        self.frequency = frequency
        self.requested_by = requested_by
        self.priority = priority
        self.metadata = metadata or {}
        self.created_at = datetime.now(timezone.utc)
        self.last_run: Optional[datetime] = None
        self.enabled = True


class AutonomousScraperService:
    """
    Manages autonomous web scraping with KG integration.
    
    Features:
    - Scheduled daily scraping for high-priority topics
    - On-demand scraping triggered by teams
    - Automatic knowledge graph ingestion
    - Intelligent deduplication
    - Audit trail for all scraping activity
    """
    
    def __init__(
        self,
        kg_service: Optional[KnowledgeGraphService] = None,
        scheduler: Optional[AsyncIOScheduler] = None
    ):
        self.settings = get_settings()
        self.kg_service = kg_service or KnowledgeGraphService()
        self.scheduler = scheduler or AsyncIOScheduler()
        
        # Initialize scrapers
        self.scrapers = {
            'california_codes': CaliforniaCodesScraper(),
            'ecfr': ECFRScraper()
        }
        
        # Track triggers and scraped content hashes
        self.triggers: Dict[str, ScrapingTrigger] = {}
        self.scraped_hashes: Set[str] = set()
        
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
    
    async def add_trigger(
        self,
        source: str,
        query: str,
        frequency: str,
        requested_by: str,
        priority: str = 'normal',
        metadata: Optional[Dict[str, Any]] = None
    ) -> ScrapingTrigger:
        """
        Add a new scraping trigger.
        
        Args:
            source: Scraper source ('california_codes', 'ecfr')
            query: Search query or topic
            frequency: 'daily' or 'on-demand'
            requested_by: Team name (e.g., 'strategy', 'research')
            priority: 'high', 'normal', 'low'
            metadata: Additional context
        """
        trigger_id = self._generate_trigger_id(source, query, requested_by)
        
        trigger = ScrapingTrigger(
            trigger_id=trigger_id,
            source=source,
            query=query,
            frequency=frequency,
            requested_by=requested_by,
            priority=priority,
            metadata=metadata
        )
        
        self.triggers[trigger_id] = trigger
        
        # Schedule if daily frequency
        if frequency == 'daily':
            self._schedule_daily_trigger(trigger)
        
        # Audit the trigger creation
        self._audit_trigger_event(
            trigger_id=trigger_id,
            action='scraper.trigger.created',
            outcome='success',
            metadata={
                'source': source,
                'query': query,
                'frequency': frequency,
                'requested_by': requested_by,
                'priority': priority
            }
        )
        
        return trigger
    
    async def execute_trigger(self, trigger_id: str) -> Dict[str, Any]:
        """
        Execute a specific trigger (on-demand or scheduled).
        
        Returns:
            Results dict with scraped content and KG ingestion status
        """
        trigger = self.triggers.get(trigger_id)
        if not trigger:
            return {'error': f'Trigger {trigger_id} not found', 'success': False}
        
        if not trigger.enabled:
            return {'error': 'Trigger is disabled', 'success': False}
        
        # Execute scraping
        results = await self.scrape_and_ingest(
            source=trigger.source,
            query=trigger.query,
            trigger_id=trigger_id
        )
        
        # Update trigger
        trigger.last_run = datetime.now(timezone.utc)
        
        return results
    
    async def scrape_and_ingest(
        self,
        source: str,
        query: str,
        trigger_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scrape from source and auto-ingest to knowledge graph.
        
        Args:
            source: Scraper to use
            query: Search query
            trigger_id: Optional trigger ID for tracking
        
        Returns:
            Dict with scraping results and KG ingestion status
        """
        scraper = self.scrapers.get(source)
        if not scraper:
            return {'error': f'Unknown source: {source}', 'success': False}
        
        try:
            # Execute scraping
            if source == 'california_codes':
                # Check if it's a section query or general search
                if '§' in query or 'section' in query.lower():
                    # Extract code and section
                    parts = query.split()
                    code = parts[0]
                    section = parts[-1].replace('§', '').strip()
                    scraped_results = [await scraper.get_code_section(code, section)]
                else:
                    scraped_results = await scraper.search_codes(query)
            elif source == 'ecfr':
                scraped_results = await scraper.search_regulations(query)
            else:
                scraped_results = []
            
            # Deduplicate and ingest to KG
            ingested_count = 0
            skipped_count = 0
            
            for result in scraped_results:
                if result is None or 'error' in result:
                    continue
                
                # Generate hash for deduplication
                content_hash = self._hash_content(result)
                
                if content_hash in self.scraped_hashes:
                    skipped_count += 1
                    continue
                
                # Ingest to knowledge graph
                await self._ingest_to_kg(source, result, query)
                
                self.scraped_hashes.add(content_hash)
                ingested_count += 1
            
            # Audit the scraping activity
            self._audit_scraping_event(
                source=source,
                query=query,
                trigger_id=trigger_id,
                ingested=ingested_count,
                skipped=skipped_count
            )
            
            return {
                'success': True,
                'source': source,
                'query': query,
                'total_results': len(scraped_results),
                'ingested': ingested_count,
                'skipped': skipped_count,
                'trigger_id': trigger_id
            }
            
        except Exception as exc:
            error_msg = f"Scraping failed: {str(exc)}"
            self._audit_scraping_event(
                source=source,
                query=query,
                trigger_id=trigger_id,
                error=error_msg
            )
            return {'error': error_msg, 'success': False}
    
    async def _ingest_to_kg(
        self,
        source: str,
        result: Dict[str, Any],
        query: str
    ) -> None:
        """Ingest scraped content to knowledge graph."""
        # Extract content
        title = result.get('title', 'Untitled')
        text = result.get('text', '')
        url = result.get('url', '')
        
        # Generate unique entity ID
        entity_id = f"statute:{source}:{self._sanitize_id(title)}"
        
        # Create LegalReference node
        await self.kg_service.add_entity(
            entity_id=entity_id,
            entity_type="LegalReference",
            properties={
                "title": title,
                "text": text[:5000],  # Limit text length
                "url": url,
                "source": source,
                "query": query,
                "scraped_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Create relationship to query topic if exists
        # (Could create Topic nodes for better organization)
    
    def _schedule_daily_trigger(self, trigger: ScrapingTrigger) -> None:
        """Schedule a trigger to run daily."""
        # Run at 2 AM daily (or configurable time)
        hour = 2
        
        if trigger.priority == 'high':
            hour = 1  # High priority runs earlier
        
        self.scheduler.add_job(
            func=self._execute_trigger_wrapper,
            trigger=CronTrigger(hour=hour, minute=0),
            args=[trigger.trigger_id],
            id=trigger.trigger_id,
            replace_existing=True
        )
    
    async def _execute_trigger_wrapper(self, trigger_id: str) -> None:
        """Wrapper for scheduler to execute triggers."""
        await self.execute_trigger(trigger_id)
    
    def remove_trigger(self, trigger_id: str) -> bool:
        """Remove a scraping trigger and its schedule."""
        if trigger_id not in self.triggers:
            return False
        
        # Remove from scheduler if scheduled
        try:
            self.scheduler.remove_job(trigger_id)
        except:
            pass  # Job might not be scheduled
        
        # Remove trigger
        del self.triggers[trigger_id]
        
        self._audit_trigger_event(
            trigger_id=trigger_id,
            action='scraper.trigger.removed',
            outcome='success',
            metadata={}
        )
        
        return True
    
    def list_triggers(self) -> List[Dict[str, Any]]:
        """List all active triggers."""
        return [
            {
                'trigger_id': t.trigger_id,
                'source': t.source,
                'query': t.query,
                'frequency': t.frequency,
                'requested_by': t.requested_by,
                'priority': t.priority,
                'enabled': t.enabled,
                'last_run': t.last_run.isoformat() if t.last_run else None,
                'created_at': t.created_at.isoformat()
            }
            for t in self.triggers.values()
        ]
    
    def _generate_trigger_id(self, source: str, query: str, requested_by: str) -> str:
        """Generate unique trigger ID."""
        content = f"{source}:{query}:{requested_by}:{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _hash_content(self, result: Dict[str, Any]) -> str:
        """Generate hash for deduplication."""
        content = f"{result.get('title', '')}:{result.get('url', '')}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _sanitize_id(self, text: str) -> str:
        """Sanitize text for use in entity IDs."""
        return text.lower().replace(' ', '_').replace('/', '_')[:100]
    
    def _audit_trigger_event(
        self,
        trigger_id: str,
        action: str,
        outcome: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Audit trigger lifecycle events."""
        event = AuditEvent(
            category='autonomous_scraper',
            action=action,
            actor={'id': 'system', 'type': 'autonomous_service'},
            subject={'trigger_id': trigger_id},
            outcome=outcome,
            severity='info',
            metadata=metadata
        )
        self.audit.append(event)
    
    def _audit_scraping_event(
        self,
        source: str,
        query: str,
        trigger_id: Optional[str] = None,
        ingested: int = 0,
        skipped: int = 0,
        error: Optional[str] = None
    ) -> None:
        """Audit scraping execution."""
        event = AuditEvent(
            category='autonomous_scraper',
            action='scraper.execute',
            actor={'id': 'system', 'type': 'autonomous_service'},
            subject={
                'source': source,
                'query': query,
                'trigger_id': trigger_id or 'manual'
            },
            outcome='success' if not error else 'error',
            severity='info' if not error else 'warning',
            metadata={
                'ingested': ingested,
                'skipped': skipped,
                'error': error
            }
        )
        self.audit.append(event)


# Singleton instance
_autonomous_scraper_service: Optional[AutonomousScraperService] = None


def get_autonomous_scraper_service() -> AutonomousScraperService:
    """Get or create the autonomous scraper service singleton."""
    global _autonomous_scraper_service
    if _autonomous_scraper_service is None:
        _autonomous_scraper_service = AutonomousScraperService()
        _autonomous_scraper_service.start_scheduler()
    return _autonomous_scraper_service
