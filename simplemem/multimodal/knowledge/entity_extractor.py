"""
Entity Extractor for Omni-Memory Knowledge Graph.

Extracts entities and relations from multimodal content using LLMs.
Supports text, image captions, and video descriptions.
"""

import logging
import json
import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

from simplemem.multimodal.core.mau import MultimodalAtomicUnit, ModalityType

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """An extracted entity from content."""
    name: str
    entity_type: str  # PERSON, OBJECT, LOCATION, EVENT, CONCEPT, etc.
    attributes: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source_mau_id: Optional[str] = None
    span: Optional[Tuple[int, int]] = None  # Character span in source text
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "attributes": self.attributes,
            "confidence": self.confidence,
            "source_mau_id": self.source_mau_id,
            "span": self.span,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractedEntity":
        return cls(**data)


@dataclass 
class ExtractedRelation:
    """An extracted relation between entities."""
    subject: str  # Entity name
    predicate: str  # Relation type
    object: str  # Entity name
    attributes: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source_mau_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "attributes": self.attributes,
            "confidence": self.confidence,
            "source_mau_id": self.source_mau_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractedRelation":
        return cls(**data)


@dataclass
class ExtractionResult:
    """Result of entity/relation extraction."""
    entities: List[ExtractedEntity]
    relations: List[ExtractedRelation]
    raw_text: str
    source_mau_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "relations": [r.to_dict() for r in self.relations],
            "raw_text": self.raw_text,
            "source_mau_id": self.source_mau_id,
        }

    def __iter__(self):
        """
        Allow unpacking like:

            entities, relations = extractor.extract(...)
        """
        yield self.entities
        yield self.relations


class EntityExtractor:
    """
    Entity and Relation Extractor using LLMs.
    
    Extracts structured knowledge from unstructured multimodal content
    to build a semantic knowledge graph.
    
    Key Features:
    - Multi-type entity extraction (PERSON, OBJECT, LOCATION, EVENT, CONCEPT)
    - Relation extraction between entities
    - Visual entity extraction from image/video captions
    - Confidence scoring for extracted elements
    """
    
    # Entity type definitions
    ENTITY_TYPES = [
        "PERSON",      # People, characters
        "OBJECT",      # Physical objects
        "LOCATION",    # Places, locations
        "EVENT",       # Events, actions
        "CONCEPT",     # Abstract concepts
        "TIME",        # Temporal references
        "ORGANIZATION", # Organizations, groups
    ]
    
    # Common relation types
    RELATION_TYPES = [
        "located_in",
        "part_of",
        "contains",
        "interacts_with",
        "owns",
        "created_by",
        "occurs_at",
        "related_to",
        "has_attribute",
        "temporal_before",
        "temporal_after",
        "causes",
    ]

    def __init__(
        self,
        config: Optional[Any] = None,
        model_name: str = "gpt-4o-mini",
    ):
        """
        Args:
            config: OmniMemoryConfig (used to read LLM settings)
            model_name: Fallback model name if config does not specify one.
        """
        self.config = config

        # Prefer config-provided model so that entity extraction uses the same
        # (or at least compatible) model as the main QA path.
        resolved_model = None
        if self.config is not None and hasattr(self.config, "llm"):
            llm_cfg = self.config.llm
            # Prefer a dedicated entity model if present, otherwise fall back
            # to summary/query model.
            candidate = getattr(llm_cfg, "entity_model", None)
            if not candidate:
                candidate = getattr(llm_cfg, "summary_model", None) or getattr(
                    llm_cfg, "query_model", None
                )
            if candidate:
                resolved_model = candidate

        if resolved_model is None:
            resolved_model = model_name

        self.model_name = resolved_model
        self._llm_client = None
        
    def _get_llm_client(self):
        """Get or create LLM client."""
        if self._llm_client is None:
            from openai import OpenAI
            import httpx
            import os
            
            client_kwargs = {}
            
            if self.config and hasattr(self.config, 'llm'):
                if self.config.llm.api_key:
                    client_kwargs["api_key"] = self.config.llm.api_key
                if self.config.llm.api_base_url:
                    client_kwargs["base_url"] = self.config.llm.api_base_url
            else:
                api_key = os.getenv("OPENAI_API_KEY")
                api_base = os.getenv("OPENAI_API_BASE")
                if api_key:
                    client_kwargs["api_key"] = api_key
                if api_base:
                    client_kwargs["base_url"] = api_base
            
            http_client = httpx.Client()
            client_kwargs["http_client"] = http_client
            
            self._llm_client = OpenAI(**client_kwargs)
        return self._llm_client

    @staticmethod
    def _parse_json_response(text: Optional[str]) -> Optional[Dict[str, Any]]:
        """Parse LLM JSON output; tolerate empty bodies, fences, and extra prose."""
        if text is None:
            return None
        s = str(text).strip()
        if not s:
            return None

        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass

        fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s)
        if fence:
            block = fence.group(1).strip()
            try:
                return json.loads(block)
            except json.JSONDecodeError:
                s = block

        start = s.find("{")
        if start < 0:
            return None
        depth = 0
        for i, ch in enumerate(s[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(s[start : i + 1])
                    except json.JSONDecodeError:
                        break
        return None

    def _call_extraction_llm(self, client, prompt: str) -> Dict[str, Any]:
        """Call LLM for entity extraction; retry without response_format for weak proxies."""
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": prompt},
        ]
        empty = {"entities": [], "relations": []}

        for use_json_format in (True, False):
            kwargs: Dict[str, Any] = {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 1024,
            }
            if use_json_format:
                kwargs["response_format"] = {"type": "json_object"}

            try:
                response = client.chat.completions.create(**kwargs)
            except Exception as exc:
                logger.debug(
                    "Entity extraction LLM call failed (json_format=%s): %s",
                    use_json_format,
                    exc,
                )
                continue

            content = (response.choices[0].message.content or "").strip()
            parsed = self._parse_json_response(content)
            if parsed is not None:
                return parsed

            if content:
                logger.debug(
                    "Entity extraction unparseable response (json_format=%s): %r",
                    use_json_format,
                    content[:200],
                )

        return empty

    def extract(
        self,
        text: Any,
        mau_id: Optional[str] = None,
        context: Optional[str] = None,
    ) -> ExtractionResult:
        """
        Extract entities and relations from content.

        This method is intentionally flexible in its input:

        - If `text` is a plain string, it is used directly.
        - If `text` is a `MultimodalAtomicUnit`, we derive a textual
          representation from its summary/details for extraction.

        Args:
            text: Text content or MAU to extract from
            mau_id: Optional source MAU ID
            context: Optional context for better extraction

        Returns:
            ExtractionResult with entities and relations
        """
        raw_text: str = ""

        # Support being called with a MAU object (backwards-compatible with older orchestrator code)
        if isinstance(text, MultimodalAtomicUnit):
            mau = text
            if mau_id is None:
                mau_id = getattr(mau, "id", None)

            try:
                if mau.modality_type == ModalityType.TEXT:
                    raw_text = mau.summary or ""
                    details = getattr(mau, "details", None)
                    if isinstance(details, dict):
                        raw_text = details.get("text", raw_text)
                    elif isinstance(details, str) and details.strip():
                        raw_text = details
                else:
                    # For non-text modalities, summary should contain caption / transcription
                    raw_text = mau.summary or ""
            except Exception:
                # Fallback to best-effort string conversion
                raw_text = str(getattr(text, "summary", "") or "")
        else:
            raw_text = str(text or "")

        if not raw_text or len(raw_text.strip()) < 10:
            return ExtractionResult(
                entities=[],
                relations=[],
                raw_text=raw_text,
                source_mau_id=mau_id,
            )

        # Build extraction prompt
        prompt = self._build_extraction_prompt(raw_text, context)
        
        client = self._get_llm_client()

        try:
            result_json = self._call_extraction_llm(client, prompt)

            # Parse entities
            entities = []
            for e in result_json.get("entities", []):
                entities.append(ExtractedEntity(
                    name=e.get("name", ""),
                    entity_type=e.get("type", "CONCEPT"),
                    attributes=e.get("attributes", {}),
                    confidence=e.get("confidence", 0.8),
                    source_mau_id=mau_id,
                ))

            # Parse relations
            relations = []
            for r in result_json.get("relations", []):
                relations.append(ExtractedRelation(
                    subject=r.get("subject", ""),
                    predicate=r.get("predicate", "related_to"),
                    object=r.get("object", ""),
                    attributes=r.get("attributes", {}),
                    confidence=r.get("confidence", 0.8),
                    source_mau_id=mau_id,
                ))

            return ExtractionResult(
                entities=entities,
                relations=relations,
                raw_text=raw_text,
                source_mau_id=mau_id,
            )

        except Exception as e:
            logger.debug("Entity extraction failed: %s", e)
            return ExtractionResult(
                entities=[],
                relations=[],
                raw_text=raw_text,
                source_mau_id=mau_id,
            )
    
    def extract_from_visual(
        self,
        caption: str,
        detailed_description: Optional[str] = None,
        mau_id: Optional[str] = None,
    ) -> ExtractionResult:
        """
        Extract entities from visual content (image/video caption).
        
        Optimized for visual descriptions with focus on:
        - Objects and their attributes
        - Spatial relationships
        - Actions and events
        """
        combined_text = caption
        if detailed_description:
            combined_text += f"\n\nDetailed description: {detailed_description}"
        
        return self.extract(
            text=combined_text,
            mau_id=mau_id,
            context="This is a description of visual content (image or video frame)."
        )
    
    def extract_batch(
        self,
        texts: List[Tuple[str, Optional[str]]],  # (text, mau_id) pairs
    ) -> List[ExtractionResult]:
        """
        Extract entities from multiple texts.
        
        Args:
            texts: List of (text, mau_id) tuples
            
        Returns:
            List of ExtractionResults
        """
        results = []
        for text, mau_id in texts:
            results.append(self.extract(text, mau_id))
        return results
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for entity extraction."""
        return """You are an expert knowledge extraction system. Extract entities and relations from the given text.

Output JSON format:
{
    "entities": [
        {
            "name": "entity name",
            "type": "PERSON|OBJECT|LOCATION|EVENT|CONCEPT|TIME|ORGANIZATION",
            "attributes": {"key": "value"},
            "confidence": 0.0-1.0
        }
    ],
    "relations": [
        {
            "subject": "entity name",
            "predicate": "relation type",
            "object": "entity name",
            "attributes": {},
            "confidence": 0.0-1.0
        }
    ]
}

Guidelines:
- Extract all meaningful entities mentioned
- Identify relationships between entities
- Use standardized entity types
- Assign confidence scores based on clarity
- For visual descriptions, pay attention to spatial relationships and object attributes"""
    
    def _build_extraction_prompt(
        self,
        text: str,
        context: Optional[str] = None,
    ) -> str:
        """Build extraction prompt."""
        prompt = f"Extract entities and relations from this text:\n\n{text}"
        
        if context:
            prompt = f"Context: {context}\n\n{prompt}"
        
        return prompt
    
    def merge_entities(
        self,
        entities: List[ExtractedEntity],
        similarity_threshold: float = 0.85,
    ) -> List[ExtractedEntity]:
        """
        Merge similar entities (entity resolution).
        
        Args:
            entities: List of extracted entities
            similarity_threshold: Threshold for merging
            
        Returns:
            Deduplicated entity list
        """
        if not entities:
            return []
        
        # Simple name-based deduplication
        # In production, use embedding similarity
        seen = {}
        merged = []
        
        for entity in entities:
            key = entity.name.lower().strip()
            
            if key in seen:
                # Merge attributes
                existing = seen[key]
                existing.attributes.update(entity.attributes)
                existing.confidence = max(existing.confidence, entity.confidence)
            else:
                seen[key] = entity
                merged.append(entity)
        
        return merged
