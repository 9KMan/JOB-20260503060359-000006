"""PII anonymization layer."""
import hashlib
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class Anonymizer:
    tenant_id: str
    _customer_map: Dict[str, str] = field(default_factory=dict)
    _product_map: Dict[str, str] = field(default_factory=dict)
    _segment_map: Dict[str, str] = field(default_factory=dict)
    _counter: Dict[str, int] = field(default_factory=lambda: {
        "customer": 0, "product": 0, "segment": 0
    })

    def _generate_hash(self, original: str) -> str:
        raw = f"{self.tenant_id}:{original}".encode()
        return hashlib.sha256(raw).hexdigest()[:8].upper()

    def _get_anonymized_id(self, original: str, entity_type: str) -> str:
        counter = self._counter[entity_type]
        self._counter[entity_type] += 1
        short_hash = self._generate_hash(original)
        return f"{entity_type.upper()[:4]}-{short_hash[:6]}"

    def anonymize(self, data: dict) -> dict:
        result = dict(data)

        if "customer_id" in result and result["customer_id"]:
            original = str(result["customer_id"])
            if original not in self._customer_map:
                self._customer_map[original] = self._get_anonymized_id(original, "customer")
            result["customer_id"] = self._customer_map[original]

        if "product_id" in result and result["product_id"]:
            original = str(result["product_id"])
            if original not in self._product_map:
                self._product_map[original] = self._get_anonymized_id(original, "product")
            result["product_id"] = self._product_map[original]

        if "customer_segment" in result and result["customer_segment"]:
            original = str(result["customer_segment"])
            if original not in self._segment_map:
                self._segment_map[original] = self._get_anonymized_id(original, "segment")
            result["customer_segment"] = self._segment_map[original]

        result.pop("customer_name", None)
        result.pop("product_name", None)
        result.pop("contact_email", None)
        result.pop("address", None)

        return result

    def anonymize_batch(self, data_list: List[dict]) -> List[dict]:
        return [self.anonymize(item) for item in data_list]

    def get_mapping(self) -> Dict[str, Dict[str, str]]:
        return {
            "customer": dict(self._customer_map),
            "product": dict(self._product_map),
            "segment": dict(self._segment_map),
        }

    def reverse_anonymize(self, anonymized_id: str, entity_type: str) -> Optional[str]:
        mapping = self.get_mapping().get(entity_type, {})
        for original, anon in mapping.items():
            if anon == anonymized_id:
                return original
        return None
