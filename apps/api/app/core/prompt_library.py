"""
Prompt Library for AI Assistance - Safety-focused templates.

All prompts include strict instructions to paraphrase and cite by article number only.
"""

from __future__ import annotations

from typing import Dict, Optional
from dataclasses import dataclass

from .validation_engine import ValidationEngine


@dataclass
class PromptTemplate:
    """Prompt template with metadata."""
    id: str
    system_prompt: str
    user_template: str
    language: str = "en"


class PromptLibrary:
    """Provide safety-focused prompt templates for AI assistance."""

    def __init__(self):
        self.validation_engine = ValidationEngine()
        
        # Safety instruction that must be included in all prompts
        self.safety_instruction = (
            "CRITICAL: You must paraphrase all content. Never quote verbatim text from UCP 600, "
            "ISBP 745, or any rulebook. Cite only article numbers (e.g., 'UCP 600 Article 14.b'). "
            "Use your own words to explain concepts. If you cannot paraphrase safely, cite the article "
            "number and provide a general explanation."
        )
    
    def get_template(self, template_name: str, language: str = "en") -> PromptTemplate:
        """
        Get prompt template by name and language.
        
        Args:
            template_name: One of: discrepancy_summary, bank_draft, amendment_draft, chat_response
            language: Language code (en, bn, ar, etc.)
        """
        if template_name == "discrepancy_summary":
            return self._get_discrepancy_summary_template(language)
        elif template_name == "bank_draft":
            return self._get_bank_draft_template(language)
        elif template_name == "amendment_draft":
            return self._get_amendment_draft_template(language)
        elif template_name == "chat_response":
            return self._get_chat_template(language)
        else:
            raise ValueError(f"Unknown template: {template_name}")
    
    def _get_discrepancy_summary_template(self, language: str) -> PromptTemplate:
        """Get discrepancy summary template."""
        if language == "bn":
            system_prompt = (
                "আপনি একজন ট্রেড ফাইন্যান্স বিশেষজ্ঞ। এলসি নথির অসঙ্গতি বিশ্লেষণ করুন এবং "
                "ব্যাখ্যা করুন। {safety_instruction}"
            ).format(safety_instruction=self.safety_instruction)
            
            user_template = (
                "নিম্নলিখিত অসঙ্গতিগুলি বিশ্লেষণ করুন:\n{discrepancies}\n\n"
                "LC ডেটা:\n{lc_data}\n\n"
                "প্রতিটি অসঙ্গতির জন্য:\n"
                "1. একটি পরিষ্কার ব্যাখ্যা (আপনার নিজের শব্দে)\n"
                "2. প্রাসঙ্গিক UCP/ISBP নিবন্ধ সংখ্যা (শুধুমাত্র সংখ্যা, উদ্ধৃতি নয়)\n"
                "3. সম্ভাব্য সমাধান পরামর্শ"
            )
        else:
            system_prompt = (
                "You are a trade finance expert. Analyze and explain LC document discrepancies. "
                "{safety_instruction}"
            ).format(safety_instruction=self.safety_instruction)
            
            user_template = (
                "Analyze the following discrepancies:\n{discrepancies}\n\n"
                "LC Data:\n{lc_data}\n\n"
                "For each discrepancy, provide:\n"
                "1. A clear explanation in your own words\n"
                "2. Relevant UCP/ISBP article numbers (numbers only, no verbatim quotes)\n"
                "3. Suggested fixes if applicable"
            )
        
        return PromptTemplate(
            id="discrepancy_summary",
            system_prompt=system_prompt,
            user_template=user_template,
            language=language
        )
    
    def _get_bank_draft_template(self, language: str) -> PromptTemplate:
        """Get bank draft letter template."""
        if language == "bn":
            system_prompt = (
                "আপনি একজন ব্যাংকিং পেশাদার। আনুষ্ঠানিক ব্যাংক নোটিশ লিখুন। "
                "{safety_instruction}"
            ).format(safety_instruction=self.safety_instruction)
            
            user_template = (
                "নিম্নলিখিত অসঙ্গতিগুলির জন্য একটি আনুষ্ঠানিক ব্যাংক নোটিশ তৈরি করুন:\n"
                "{discrepancy_list}\n\n"
                "LC তথ্য:\n{lc_data}\n\n"
                "নোটিশে অন্তর্ভুক্ত করুন:\n"
                "1. আনুষ্ঠানিক ব্যাংকিং ভাষা\n"
                "2. UCP/ISBP নিবন্ধ সংখ্যা (উদ্ধৃতি নয়)\n"
                "3. পরিষ্কার এবং সংক্ষিপ্ত ভাষা"
            )
        else:
            system_prompt = (
                "You are a banking professional. Write formal bank notifications. "
                "{safety_instruction}"
            ).format(safety_instruction=self.safety_instruction)
            
            user_template = (
                "Create a formal bank notice for the following discrepancies:\n"
                "{discrepancy_list}\n\n"
                "LC Information:\n{lc_data}\n\n"
                "Include in the notice:\n"
                "1. Professional banking language\n"
                "2. UCP/ISBP article numbers (not verbatim quotes)\n"
                "3. Clear and concise language"
            )
        
        return PromptTemplate(
            id="bank_draft",
            system_prompt=system_prompt,
            user_template=user_template,
            language=language
        )
    
    def _get_amendment_draft_template(self, language: str) -> PromptTemplate:
        """Get amendment draft template."""
        if language == "bn":
            system_prompt = (
                "আপনি একজন ট্রেড ফাইন্যান্স বিশেষজ্ঞ। এলসি সংশোধনী খসড়া তৈরি করুন। "
                "{safety_instruction}"
            ).format(safety_instruction=self.safety_instruction)
            
            user_template = (
                "একটি সংশোধনী খসড়া তৈরি করুন:\n"
                "সংশোধনী ধরন: {amendment_type}\n"
                "বিবরণ: {amendment_details}\n\n"
                "LC তথ্য:\n{lc_data}\n\n"
                "সংশোধনীতে অন্তর্ভুক্ত করুন:\n"
                "1. স্পষ্ট এবং নির্দিষ্ট ভাষা\n"
                "2. প্রাসঙ্গিক UCP নিবন্ধ সংখ্যা\n"
                "3. প্রয়োজনীয় বিবরণ"
            )
        else:
            system_prompt = (
                "You are a trade finance expert. Draft LC amendments. "
                "{safety_instruction}"
            ).format(safety_instruction=self.safety_instruction)
            
            user_template = (
                "Draft an amendment:\n"
                "Amendment Type: {amendment_type}\n"
                "Details: {amendment_details}\n\n"
                "LC Information:\n{lc_data}\n\n"
                "Include in the amendment:\n"
                "1. Clear and specific language\n"
                "2. Relevant UCP article numbers\n"
                "3. Required details"
            )
        
        return PromptTemplate(
            id="amendment_draft",
            system_prompt=system_prompt,
            user_template=user_template,
            language=language
        )
    
    def _get_chat_template(self, language: str) -> PromptTemplate:
        """Get chat response template."""
        if language == "bn":
            system_prompt = (
                "আপনি একজন ট্রেড ফাইন্যান্স সহায়ক। ব্যবহারকারীর প্রশ্নের উত্তর দিন। "
                "{safety_instruction}"
            ).format(safety_instruction=self.safety_instruction)
            
            user_template = (
                "প্রশ্ন: {question}\n\n"
                "LC প্রসঙ্গ:\n{lc_data}\n\n"
                "অসঙ্গতি:\n{discrepancies}\n\n"
                "একটি সহায়ক উত্তর প্রদান করুন যা:\n"
                "1. প্রশ্নের সরাসরি উত্তর দেয়\n"
                "2. প্রাসঙ্গিক নিবন্ধ সংখ্যা উল্লেখ করে (উদ্ধৃতি নয়)\n"
                "3. পরিষ্কার এবং বোধগম্য ভাষায়"
            )
        else:
            system_prompt = (
                "You are a trade finance assistant. Answer user questions. "
                "{safety_instruction}"
            ).format(safety_instruction=self.safety_instruction)
            
            user_template = (
                "Question: {question}\n\n"
                "LC Context:\n{lc_data}\n\n"
                "Discrepancies:\n{discrepancies}\n\n"
                "Provide a helpful answer that:\n"
                "1. Directly addresses the question\n"
                "2. References relevant article numbers (not verbatim quotes)\n"
                "3. Uses clear and understandable language"
            )
        
        return PromptTemplate(
            id="chat_response",
            system_prompt=system_prompt,
            user_template=user_template,
            language=language
        )
    
    def get_bank_template(self, language):
        """Return a simple bank discrepancy notification template (legacy)."""
        if str(language).lower().startswith("bn"):
            return "ব্যাংক অবহিতকরণ:\n{discrepancies}\nতারিখ: {date}"
        return "Bank Notice:\n{discrepancies}\nDate: {date}"

    def get_amendment_template(self, amendment_type: str, language):
        """Return a formatted amendment template (legacy)."""
        if str(language).lower().startswith("bn"):
            return "অ্যামেন্ডমেন্ট ({amendment_type}): {details}"
        return "Amendment ({amendment_type}): {details}"

    def get_chat_help_prompts(self) -> Dict[str, str]:
        """Return canned chat helper prompts (legacy)."""
        return {
            "en": "How can I help you with your LC validation?",
            "bn": "আমি কীভাবে আপনার এলসি যাচাইকরণে সাহায্য করতে পারি?",
        }
