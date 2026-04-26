"""PolitiKAST simulation core.

Public surface (kept narrow on purpose):
- VoterAgent: persona-conditioned vote sampler.
- ElectionEnv: timestep loop + tally.
- consensus / bandwagon_underdog: poll aggregation.
- run_scenario.run_region: end-to-end region runner.
"""
from .voter_agent import VoterAgent  # noqa: F401
from .election_env import ElectionEnv  # noqa: F401
from .poll_consensus import consensus, bandwagon_underdog  # noqa: F401
