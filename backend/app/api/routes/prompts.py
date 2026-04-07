"""Prompt management API — view and hot-update agent system prompts."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import get_current_user
from app.agents.orchestrator import STAGE_DEFINITIONS

router = APIRouter(prefix="/prompts", tags=["prompts"])

# Runtime prompt overrides (in-memory; persisted via DB in production)
_prompt_overrides: dict[str, str] = {}


class PromptUpdate(BaseModel):
    agent_name: str
    system_prompt: str


class PromptInfo(BaseModel):
    agent_name: str
    stage_number: int
    description: str
    system_prompt: str
    is_overridden: bool
    prompt_length: int


@router.get("", response_model=list[PromptInfo])
async def list_prompts(user: dict = Depends(get_current_user)):
    """List all agent system prompts."""
    from app.core.llm import LLMClient

    dummy_llm = LLMClient()
    result = []

    for defn in STAGE_DEFINITIONS:
        cls = defn["agent"]
        if cls is None:
            continue

        agent = cls(dummy_llm)
        override = _prompt_overrides.get(agent.name)
        prompt = override if override else agent.system_prompt

        result.append(PromptInfo(
            agent_name=agent.name,
            stage_number=agent.stage_number,
            description=agent.description,
            system_prompt=prompt,
            is_overridden=agent.name in _prompt_overrides,
            prompt_length=len(prompt),
        ))

    return result


@router.get("/{agent_name}", response_model=PromptInfo)
async def get_prompt(agent_name: str, user: dict = Depends(get_current_user)):
    """Get a specific agent's system prompt."""
    from app.core.llm import LLMClient

    dummy_llm = LLMClient()

    for defn in STAGE_DEFINITIONS:
        cls = defn["agent"]
        if cls is None:
            continue
        agent = cls(dummy_llm)
        if agent.name == agent_name:
            override = _prompt_overrides.get(agent.name)
            return PromptInfo(
                agent_name=agent.name,
                stage_number=agent.stage_number,
                description=agent.description,
                system_prompt=override if override else agent.system_prompt,
                is_overridden=agent.name in _prompt_overrides,
                prompt_length=len(override if override else agent.system_prompt),
            )

    raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")


@router.put("/{agent_name}")
async def update_prompt(
    agent_name: str,
    data: PromptUpdate,
    user: dict = Depends(get_current_user),
):
    """Hot-update an agent's system prompt (runtime override)."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    # Verify agent exists
    from app.core.llm import LLMClient
    dummy_llm = LLMClient()
    found = False
    for defn in STAGE_DEFINITIONS:
        cls = defn["agent"]
        if cls is None:
            continue
        agent = cls(dummy_llm)
        if agent.name == agent_name:
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    _prompt_overrides[agent_name] = data.system_prompt

    # Invalidate cache for this agent
    try:
        from app.services.agent_cache import get_agent_cache
        cache = get_agent_cache()
        count = await cache.invalidate_agent(agent_name)
    except Exception:
        count = 0

    return {
        "message": f"Prompt updated for '{agent_name}'",
        "cache_invalidated": count,
    }


@router.delete("/{agent_name}")
async def reset_prompt(
    agent_name: str,
    user: dict = Depends(get_current_user),
):
    """Reset an agent's prompt to its built-in default."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    if agent_name in _prompt_overrides:
        del _prompt_overrides[agent_name]

    return {"message": f"Prompt reset to default for '{agent_name}'"}


def get_effective_prompt(agent_name: str, default_prompt: str) -> str:
    """Get the effective prompt (override or default). Used by BaseAgent."""
    return _prompt_overrides.get(agent_name, default_prompt)
