import logging
from typing import List

from app.utils.llm_utils import async_llm_request
from assets.prompts import (
    PIPELINE_QUESTION_GENERATOR_PROMPT,
    PIPELINE_QUESTION_GENERATOR_USER_PROMPT,
)
from app.database.db import search_knowledge
from app.database.models import Chunk, ChunkType, GradeLevel, Resource, Subject
from app.config import llm_settings

logger = logging.getLogger(__name__)


async def generate_exercise(
    query: str,
    subject: Subject = Subject.geography,
    grade_level: GradeLevel = GradeLevel.os2,
) -> str:

    # TODO: Add a global setting to store the resource ID for the user
    # TODO: Redesign this function to search on only the relevant resources
    # Retrieve the relevant content and exercises
    retrieved_content = await search_knowledge(
        query=query,
        n_results=7,
        where={
            Chunk.content_type: [ChunkType.text],
            Chunk.resource_id: [4],
        },  # TODO: Change this to the relevant resource IDs for the subject, grade_level, and user
    )
    retrieved_exercises = await search_knowledge(
        query=query,
        n_results=3,
        where={
            Chunk.content_type: [ChunkType.exercise],
            Chunk.resource_id: [4],
        },
    )

    logger.debug(
        f"Retrieved {len(retrieved_content)} content chunks, this is the first: {retrieved_content[0]}"
    )
    logger.debug(
        f"Retrieved {len(retrieved_content)} exercise chunks, this is the first: {retrieved_content[0]}"
    )

    # Format the context and prompt
    context = _format_context(retrieved_content, retrieved_exercises)
    system_prompt = PIPELINE_QUESTION_GENERATOR_PROMPT.format()
    user_prompt = PIPELINE_QUESTION_GENERATOR_USER_PROMPT.format(
        query=query, context_str=context
    )

    # Generate a question based on the context
    return await _generate(system_prompt, user_prompt)


async def _generate(prompt: str, query: str, verbose: bool = False) -> str:
    try:
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": query},
        ]

        if verbose:
            print(f"--------------------------")
            print(f"System prompt: \n{prompt}")
            print(f"--------------------------")
            print(f"User prompt: \n{query}")

        res = await async_llm_request(
            llm=llm_settings.exercise_generator_model,
            verbose=False,
            messages=messages,
            max_tokens=100,
        )

        return res.choices[0].message.content

    except Exception as e:
        logger.error(f"An error occurred when generating a response query: {e}")
        return None


def _format_context(
    retrieved_content: List[Chunk],
    retrieved_exercise: List[Chunk],
    resources: List[Resource],
):
    # Formatting the context
    context_parts = []
    if len(resources) == 1:
        context_parts.append(f"### Context from the resource ({resources[0].name})\n")
    else:
        # TODO: Make this neater another time
        resource_titles = ", ".join(
            [f"{resource.id}. {resource.name}" for resource in resources]
        )
        context_parts.append(f"### Context from the resources ({resource_titles})\n")

    for chunk in retrieved_content + retrieved_exercise:
        # TODO: Make this neater another time
        if chunk.top_level_section_title and chunk.top_level_section_index:
            heading = f"-{chunk.content_type} from chapter {chunk.top_level_section_index}. {chunk.top_level_section_title} in resource {chunk.resource_id}"
        elif chunk.top_level_section_title:
            heading = f"-{chunk.content_type} from section {chunk.top_level_section_title} in resource {chunk.resource_id}"
        else:
            heading = f"-{chunk.content_type} from resource {chunk.resource_id}"

    context_parts.append(heading)
    context_parts.append(f"{chunk.content}")

    return "\n".join(context_parts)
