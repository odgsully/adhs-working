"""
Professional Services Blacklist Module - Enhanced Dynamic Version
==================================================================

Provides multi-tiered filtering to identify professional service companies:
- Tier 1: Exact match (static blacklist)
- Tier 2: Keyword detection
- Tier 3: Fuzzy matching
- Tier 4: Pattern detection
- Tier 5: Learning component with tracking

"""

from pathlib import Path
from typing import Set, Optional, Dict, List, Tuple
import logging
import re
import json
from collections import Counter
from datetime import datetime

try:
    from rapidfuzz import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    print("⚠️ Warning: rapidfuzz not installed - fuzzy matching disabled")

logger = logging.getLogger(__name__)

class StatutoryAgentBlacklist:
    """Enhanced dynamic blacklist with multi-tier filtering and learning."""

    # Tier 2: Keywords that indicate professional services
    BLACKLIST_KEYWORDS = [
        'REGISTERED AGENT',
        'STATUTORY AGENT',
        'CORPORATION SERVICE',
        'CT CORPORATION',
        'INCORP SERVICE',
        'BUSINESS FILING',
        'AGENT SERVICE',
        'AGENT LLC',
        'AGENT INC',
        'COGENCY GLOBAL',
        'PARACORP',
        'NORTHWEST REGISTERED',
        'LEGALZOOM',
    ]

    # Keywords to exclude (not professional services)
    EXCLUSION_KEYWORDS = [
        'REAL ESTATE',
        'INSURANCE AGENT',
        'REALTY',
        'TRAVEL AGENT',
    ]

    # Tier 4: Pattern regexes for professional services
    SERVICE_PATTERNS = [
        r'^[A-Z\s&]+(?:AGENT|AGENTS|SERVICE|SERVICES)\s*(?:LLC|INC\.?|CORP\.?|COMPANY)?\s*$',
        r'^[A-Z\s&]+STATUTORY\s+(?:AGENT|AGENTS|SERVICE|SERVICES)',
        r'^[A-Z\s&]+REGISTERED\s+(?:AGENT|AGENTS)',
        r'\b(?:CSC|CT)\s+(?:CORP|CORPORATION)',
        r'^(?:CORPORATE|BUSINESS)\s+(?:FILING|FILINGS|SERVICE)',
    ]

    def __init__(self, blacklist_file: Optional[Path] = None,
                 tracking_file: Optional[Path] = None,
                 enable_learning: bool = True):
        """
        Initialize enhanced blacklist with learning capabilities.

        Args:
            blacklist_file: Path to static blacklist file
            tracking_file: Path to tracking/learning data file
            enable_learning: Enable Tier 5 learning component
        """
        if blacklist_file is None:
            blacklist_file = Path(__file__).parent / "statutory_agent_blacklist.txt"

        if tracking_file is None:
            tracking_file = Path(__file__).parent / "agent_tracking_data.json"

        self.blacklist_file = blacklist_file
        self.tracking_file = tracking_file
        self.blacklist: Set[str] = set()
        self.enable_learning = enable_learning

        # Tier 5: Learning component tracking
        self.agent_counter: Counter = Counter()
        self.unknown_agents: Dict[str, Dict] = {}
        self.suggested_blacklist: Set[str] = set()

        self._load_blacklist()
        self._load_tracking_data()

        # Compile patterns for efficiency
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.SERVICE_PATTERNS]

    def _load_blacklist(self) -> None:
        """Load blacklist from file."""
        if not self.blacklist_file.exists():
            logger.warning(f"Blacklist file not found: {self.blacklist_file}")
            return

        try:
            with open(self.blacklist_file, 'r') as f:
                for line in f:
                    # Skip comments and empty lines
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Store as uppercase for case-insensitive matching
                        self.blacklist.add(line.upper())

            logger.info(f"Loaded {len(self.blacklist)} entries from blacklist")

        except Exception as e:
            logger.error(f"Error loading blacklist: {e}")

    def _load_tracking_data(self) -> None:
        """Load learning component tracking data."""
        if not self.enable_learning:
            return

        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, 'r') as f:
                    data = json.load(f)
                    self.agent_counter = Counter(data.get('counter', {}))
                    self.unknown_agents = data.get('unknown', {})
                    self.suggested_blacklist = set(data.get('suggested', []))
                    logger.info(f"Loaded tracking data: {len(self.agent_counter)} agents tracked")
            except Exception as e:
                logger.error(f"Error loading tracking data: {e}")

    def _save_tracking_data(self) -> None:
        """Save learning component tracking data."""
        if not self.enable_learning:
            return

        try:
            data = {
                'counter': dict(self.agent_counter),
                'unknown': self.unknown_agents,
                'suggested': list(self.suggested_blacklist),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.tracking_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving tracking data: {e}")

    def _check_keyword_match(self, name_upper: str) -> bool:
        """Tier 2: Check for keyword matches."""
        # Check exclusions first
        for exclusion in self.EXCLUSION_KEYWORDS:
            if exclusion in name_upper:
                return False

        # Check blacklist keywords
        for keyword in self.BLACKLIST_KEYWORDS:
            if keyword in name_upper:
                return True

        return False

    def _check_fuzzy_match(self, name_upper: str, threshold: int = 85) -> bool:
        """Tier 3: Check fuzzy string matching."""
        if not FUZZY_AVAILABLE:
            return False

        for blacklisted in self.blacklist:
            if fuzz.token_sort_ratio(name_upper, blacklisted) >= threshold:
                return True

        return False

    def _check_pattern_match(self, name_upper: str) -> bool:
        """Tier 4: Check regex pattern matching."""
        for pattern in self.compiled_patterns:
            if pattern.search(name_upper):
                # Double-check it's not excluded
                for exclusion in self.EXCLUSION_KEYWORDS:
                    if exclusion in name_upper:
                        return False
                return True

        return False

    def _track_agent(self, name: str, is_blocked: bool) -> None:
        """Tier 5: Track agent for learning component."""
        if not self.enable_learning or not name:
            return

        name_upper = str(name).strip().upper()
        self.agent_counter[name_upper] += 1

        # Track unknown agents (not in static blacklist)
        if not is_blocked and name_upper not in self.blacklist:
            if name_upper not in self.unknown_agents:
                self.unknown_agents[name_upper] = {
                    'first_seen': datetime.now().isoformat(),
                    'count': 0,
                    'suggested': False
                }
            self.unknown_agents[name_upper]['count'] += 1

            # Suggest for blacklist if appears frequently and matches patterns
            if self.unknown_agents[name_upper]['count'] >= 10:
                if self._check_keyword_match(name_upper) or self._check_pattern_match(name_upper):
                    if not self.unknown_agents[name_upper]['suggested']:
                        self.suggested_blacklist.add(name_upper)
                        self.unknown_agents[name_upper]['suggested'] = True
                        logger.info(f"Suggested for blacklist: {name_upper} (count: {self.unknown_agents[name_upper]['count']})")

        # Periodically save (every 100 checks)
        if sum(self.agent_counter.values()) % 100 == 0:
            self._save_tracking_data()

    def is_blacklisted(self, name: str) -> bool:
        """
        Enhanced multi-tier check if a statutory agent name is blacklisted.

        Tiers:
        1. Exact match (static blacklist)
        2. Keyword detection
        3. Fuzzy matching (85% threshold)
        4. Pattern detection
        5. Learning/tracking

        Args:
            name: Statutory agent name to check

        Returns:
            True if name is a professional service (blacklisted), False otherwise
        """
        if not name:
            return False

        name_upper = str(name).strip().upper()

        # Tier 1: Exact match
        if name_upper in self.blacklist:
            self._track_agent(name, True)
            return True

        # Check for common variations
        name_no_punct = name_upper.rstrip('.,')
        if name_no_punct in self.blacklist:
            self._track_agent(name, True)
            return True

        # Tier 2: Keyword detection
        if self._check_keyword_match(name_upper):
            self._track_agent(name, True)
            return True

        # Tier 3: Fuzzy matching
        if self._check_fuzzy_match(name_upper):
            self._track_agent(name, True)
            return True

        # Tier 4: Pattern detection
        if self._check_pattern_match(name_upper):
            self._track_agent(name, True)
            return True

        # Not blacklisted - track for learning
        self._track_agent(name, False)
        return False

    def is_individual(self, name: str) -> bool:
        """
        Check if a statutory agent appears to be an individual (not blacklisted).

        Args:
            name: Statutory agent name to check

        Returns:
            True if name appears to be an individual, False if professional service
        """
        return not self.is_blacklisted(name)

    def filter_agents(self, agents: list) -> list:
        """
        Filter a list of statutory agents, removing blacklisted ones.

        Args:
            agents: List of agent names or dictionaries with 'name' field

        Returns:
            Filtered list with professional services removed
        """
        filtered = []

        for agent in agents:
            # Handle both string names and dict records
            if isinstance(agent, str):
                name = agent
                if self.is_individual(name):
                    filtered.append(agent)
            elif isinstance(agent, dict) and 'name' in agent:
                name = agent['name']
                if self.is_individual(name):
                    filtered.append(agent)
            else:
                # If we can't determine the name, keep it (conservative approach)
                filtered.append(agent)

        return filtered

    def get_stats(self) -> dict:
        """Get enhanced statistics about the blacklist and learning component."""
        stats = {
            'tier1_static_entries': len(self.blacklist),
            'tier2_keywords': len(self.BLACKLIST_KEYWORDS),
            'tier4_patterns': len(self.SERVICE_PATTERNS),
            'file_path': str(self.blacklist_file),
            'file_exists': self.blacklist_file.exists()
        }

        if self.enable_learning:
            stats.update({
                'tier5_agents_tracked': len(self.agent_counter),
                'tier5_unknown_agents': len(self.unknown_agents),
                'tier5_suggested_additions': len(self.suggested_blacklist),
                'tier5_total_checks': sum(self.agent_counter.values())
            })

        return stats

    def get_learning_report(self) -> Dict[str, any]:
        """Generate a report of learning component discoveries."""
        if not self.enable_learning:
            return {'error': 'Learning component not enabled'}

        # Find frequently appearing unknown agents
        frequent_unknowns = [
            (name, data) for name, data in self.unknown_agents.items()
            if data['count'] >= 5
        ]
        frequent_unknowns.sort(key=lambda x: x[1]['count'], reverse=True)

        return {
            'suggested_for_blacklist': list(self.suggested_blacklist),
            'frequent_unknowns': [
                {
                    'name': name,
                    'count': data['count'],
                    'first_seen': data['first_seen'],
                    'suggested': data['suggested']
                }
                for name, data in frequent_unknowns[:20]
            ],
            'total_agents_tracked': len(self.agent_counter),
            'total_checks': sum(self.agent_counter.values()),
            'tracking_file': str(self.tracking_file)
        }

    def approve_suggestions(self, names_to_approve: List[str]) -> bool:
        """
        Approve suggested names to add to the permanent blacklist.

        Args:
            names_to_approve: List of names to add to blacklist

        Returns:
            True if successfully updated
        """
        try:
            # Add to in-memory blacklist
            for name in names_to_approve:
                name_upper = name.upper().strip()
                self.blacklist.add(name_upper)
                # Remove from suggestions
                self.suggested_blacklist.discard(name_upper)

            # Append to file
            with open(self.blacklist_file, 'a') as f:
                f.write(f"\n# Added by learning component - {datetime.now().isoformat()}\n")
                for name in names_to_approve:
                    f.write(f"{name}\n")

            # Update tracking data
            self._save_tracking_data()

            logger.info(f"Approved {len(names_to_approve)} additions to blacklist")
            return True

        except Exception as e:
            logger.error(f"Error approving suggestions: {e}")
            return False


# Convenience function for simple usage
_default_blacklist = None

def is_professional_service(name: str) -> bool:
    """
    Check if a statutory agent name is a professional service.

    Uses default blacklist file location.

    Args:
        name: Statutory agent name to check

    Returns:
        True if professional service, False if individual
    """
    global _default_blacklist
    if _default_blacklist is None:
        _default_blacklist = StatutoryAgentBlacklist()

    return _default_blacklist.is_blacklisted(name)


def is_individual_agent(name: str) -> bool:
    """
    Check if a statutory agent name is an individual (not professional service).

    Uses default blacklist file location.

    Args:
        name: Statutory agent name to check

    Returns:
        True if individual, False if professional service
    """
    return not is_professional_service(name)


if __name__ == "__main__":
    # Test the blacklist
    blacklist = StatutoryAgentBlacklist()

    print("Blacklist Statistics:")
    print(blacklist.get_stats())

    # Test some known entries
    test_names = [
        "CORPORATION SERVICE COMPANY",
        "Corporation Service Company",
        "CT CORPORATION SYSTEM",
        "Trula Breuninger",  # Individual - should NOT be blacklisted
        "Joe Keeper",  # Individual - should NOT be blacklisted
        "COGENCY GLOBAL INC",
        "John Smith",  # Generic individual - should NOT be blacklisted
    ]

    print("\nTest Results:")
    for name in test_names:
        is_blocked = blacklist.is_blacklisted(name)
        status = "BLOCKED" if is_blocked else "ALLOWED"
        print(f"  {name:<40} -> {status}")