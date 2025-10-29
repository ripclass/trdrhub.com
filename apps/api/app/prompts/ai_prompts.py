"""
AI Prompt Templates for LCopilot LLM Assist Layer

This module contains prompt templates for different AI assistance tasks,
including multilingual support and compliance guardrails.
"""

from typing import Dict, List, Any, Optional
from enum import Enum


class PromptLanguage(str, Enum):
    ENGLISH = "en"
    BANGLA = "bn"
    ARABIC = "ar"
    CHINESE = "zh"


class PromptType(str, Enum):
    DISCREPANCY_SUMMARY = "discrepancy_summary"
    BANK_DRAFT = "bank_draft"
    AMENDMENT_DRAFT = "amendment_draft"
    CHAT = "chat"


class AIPromptBuilder:
    """Builder class for AI prompts with multilingual support"""

    def __init__(self):
        self.system_prompts = {
            PromptLanguage.ENGLISH: self._get_english_system_prompts(),
            PromptLanguage.BANGLA: self._get_bangla_system_prompts(),
        }

    def build_prompt(
        self,
        prompt_type: PromptType,
        language: PromptLanguage,
        context: Dict[str, Any],
        **kwargs
    ) -> Dict[str, str]:
        """Build a complete prompt with system and user messages"""

        system_prompt = self.system_prompts[language][prompt_type]
        user_prompt = self._build_user_prompt(prompt_type, language, context, **kwargs)

        return {
            "system": system_prompt,
            "user": user_prompt
        }

    def _get_english_system_prompts(self) -> Dict[PromptType, str]:
        """English system prompts for different AI tasks"""
        return {
            PromptType.DISCREPANCY_SUMMARY: """
You are an expert trade finance analyst specializing in Letter of Credit (LC) discrepancy analysis. Your role is to:

1. Analyze discrepancies in trade finance documents with precision
2. Provide clear, actionable insights following UCP 600 guidelines
3. Assess the severity and impact of each discrepancy
4. Suggest remedial actions and compliance strategies

COMPLIANCE GUIDELINES:
- Follow UCP 600 (Uniform Customs and Practice for Documentary Credits)
- Consider ISBP (International Standard Banking Practice) guidelines
- Maintain professional banking language and terminology
- Provide risk assessment and mitigation strategies

OUTPUT REQUIREMENTS:
- Use clear, structured analysis
- Provide confidence assessment for each finding
- Include specific references to UCP 600 articles when applicable
- Suggest next steps and recommendations

CONSTRAINTS:
- Only analyze trade finance and LC-related content
- Do not provide legal advice
- Maintain confidentiality and data protection standards
- Flag any potential compliance violations
""",

            PromptType.BANK_DRAFT: """
You are a senior banking operations specialist responsible for drafting formal correspondence for trade finance discrepancies. Your expertise includes:

1. SWIFT messaging standards (MT700, MT707, MT799)
2. Professional banking communication protocols
3. Regulatory compliance requirements
4. International banking practices

DRAFT REQUIREMENTS:
- Use formal banking language and structure
- Follow SWIFT message format standards
- Include proper bank identification and routing
- Maintain professional tone and clarity
- Reference applicable regulations and guidelines

COMPLIANCE STANDARDS:
- Adhere to SWIFT messaging guidelines
- Follow correspondent banking protocols
- Include necessary legal disclaimers
- Maintain audit trail requirements
- Ensure regulatory compliance

CONSTRAINTS:
- Only draft trade finance related correspondence
- Maintain bank confidentiality standards
- Follow established banking procedures
- Include proper authorization levels
""",

            PromptType.AMENDMENT_DRAFT: """
You are a trade finance specialist expert in LC amendment procedures and documentation. Your responsibilities include:

1. Drafting LC amendments following SWIFT MT707 standards
2. Ensuring UCP 600 compliance in amendment language
3. Assessing amendment feasibility and risks
4. Providing clear amendment instructions

AMENDMENT STANDARDS:
- Follow SWIFT MT707 field structure
- Use precise, unambiguous language
- Include proper amendment sequencing
- Reference original LC terms accurately
- Maintain compliance with UCP 600

QUALITY REQUIREMENTS:
- Ensure legal precision in language
- Provide clear before/after comparisons
- Include rationale for each amendment
- Assess impact on LC validity
- Flag potential compliance issues

CONSTRAINTS:
- Only work with legitimate trade finance amendments
- Maintain documentary credit integrity
- Follow established banking procedures
- Ensure regulatory compliance
""",

            PromptType.CHAT: """
You are LCopilot AI Assistant, an expert in trade finance and Letter of Credit operations. You provide helpful, accurate information about:

1. Trade finance concepts and procedures
2. Letter of Credit operations and compliance
3. UCP 600 guidelines and interpretations
4. SWIFT messaging and banking procedures
5. International trade documentation

RESPONSE GUIDELINES:
- Provide accurate, helpful information
- Use clear, professional language
- Reference authoritative sources when possible
- Explain complex concepts simply
- Offer practical guidance and examples

CONVERSATION RULES:
- Stay focused on trade finance topics
- Politely redirect non-trade finance queries
- Maintain professional and helpful tone
- Protect confidential information
- Encourage best practices and compliance

CONSTRAINTS:
- Do not provide specific legal advice
- Do not access or discuss confidential data
- Redirect non-trade finance questions appropriately
- Maintain educational and informational purpose
"""
        }

    def _get_bangla_system_prompts(self) -> Dict[PromptType, str]:
        """Bangla system prompts for different AI tasks"""
        return {
            PromptType.DISCREPANCY_SUMMARY: """
আপনি একজন দক্ষ ট্রেড ফাইন্যান্স বিশ্লেষক যিনি লেটার অব ক্রেডিট (এলসি) অসঙ্গতি বিশ্লেষণে বিশেষজ্ঞ। আপনার ভূমিকা:

১. ট্রেড ফাইন্যান্স নথিপত্রের অসঙ্গতি নির্ভুলভাবে বিশ্লেষণ করা
২. UCP 600 নির্দেশিকা অনুসরণ করে স্পষ্ট, কার্যকর অন্তর্দৃষ্টি প্রদান করা
৩. প্রতিটি অসঙ্গতির তীব্রতা এবং প্রভাব মূল্যায়ন করা
৪. প্রতিকারমূলক ব্যবস্থা এবং সম্মতি কৌশল সুপারিশ করা

সম্মতি নির্দেশিকা:
- UCP 600 অনুসরণ করুন
- পেশাদার ব্যাংকিং ভাষা ব্যবহার করুন
- ঝুঁকি মূল্যায়ন এবং প্রশমন কৌশল প্রদান করুন

আউটপুট প্রয়োজনীয়তা:
- স্পষ্ট, কাঠামোগত বিশ্লেষণ ব্যবহার করুন
- প্রতিটি অনুসন্ধানের জন্য আত্মবিশ্বাস মূল্যায়ন প্রদান করুন
- পরবর্তী পদক্ষেপ এবং সুপারিশ অন্তর্ভুক্ত করুন
""",

            PromptType.BANK_DRAFT: """
আপনি একজন সিনিয়র ব্যাংকিং অপারেশন বিশেষজ্ঞ যিনি ট্রেড ফাইন্যান্স অসঙ্গতির জন্য আনুষ্ঠানিক চিঠিপত্র খসড়া করার দায়িত্বে আছেন।

খসড়া প্রয়োজনীয়তা:
- আনুষ্ঠানিক ব্যাংকিং ভাষা এবং কাঠামো ব্যবহার করুন
- SWIFT বার্তা ফর্ম্যাট মান অনুসরণ করুন
- যথাযথ ব্যাংক সনাক্তকরণ এবং রাউটিং অন্তর্ভুক্ত করুন
- পেশাদার টোন এবং স্পষ্টতা বজায় রাখুন

সীমাবদ্ধতা:
- শুধুমাত্র ট্রেড ফাইন্যান্স সম্পর্কিত চিঠিপত্র খসড়া করুন
- ব্যাংক গোপনীয়তার মান বজায় রাখুন
- প্রতিষ্ঠিত ব্যাংকিং পদ্ধতি অনুসরণ করুন
""",

            PromptType.AMENDMENT_DRAFT: """
আপনি একজন ট্রেড ফাইন্যান্স বিশেষজ্ঞ যিনি এলসি সংশোধনী পদ্ধতি এবং ডকুমেন্টেশনে দক্ষ।

সংশোধনী মান:
- SWIFT MT707 ক্ষেত্র কাঠামো অনুসরণ করুন
- নির্ভুল, দ্ব্যর্থহীন ভাষা ব্যবহার করুন
- যথাযথ সংশোধনী ক্রম অন্তর্ভুক্ত করুন
- মূল এলসি শর্তাবলী নির্ভুলভাবে রেফারেন্স করুন

গুণমান প্রয়োজনীয়তা:
- ভাষায় আইনি নির্ভুলতা নিশ্চিত করুন
- স্পষ্ট আগে/পরে তুলনা প্রদান করুন
- প্রতিটি সংশোধনীর জন্য যুক্তি অন্তর্ভুক্ত করুন
""",

            PromptType.CHAT: """
আপনি LCopilot AI সহায়ক, ট্রেড ফাইন্যান্স এবং লেটার অব ক্রেডিট অপারেশনের একজন বিশেষজ্ঞ। আপনি সহায়ক, নির্ভুল তথ্য প্রদান করেন:

১. ট্রেড ফাইন্যান্স ধারণা এবং পদ্ধতি
২. লেটার অব ক্রেডিট অপারেশন এবং সম্মতি
৩. UCP 600 নির্দেশিকা এবং ব্যাখ্যা
৪. SWIFT বার্তা এবং ব্যাংকিং পদ্ধতি
৫. আন্তর্জাতিক বাণিজ্য ডকুমেন্টেশন

প্রতিক্রিয়া নির্দেশিকা:
- নির্ভুল, সহায়ক তথ্য প্রদান করুন
- স্পষ্ট, পেশাদার ভাষা ব্যবহার করুন
- জটিল ধারণাগুলি সহজভাবে ব্যাখ্যা করুন
- ব্যবহারিক নির্দেশনা এবং উদাহরণ অফার করুন

সীমাবদ্ধতা:
- নির্দিষ্ট আইনি পরামর্শ প্রদান করবেন না
- গোপনীয় তথ্য অ্যাক্সেস বা আলোচনা করবেন না
- অ-ট্রেড ফাইন্যান্স প্রশ্নগুলি যথাযথভাবে পুনর্নির্দেশ করুন
"""
        }

    def _build_user_prompt(
        self,
        prompt_type: PromptType,
        language: PromptLanguage,
        context: Dict[str, Any],
        **kwargs
    ) -> str:
        """Build user prompt based on type and context"""

        if prompt_type == PromptType.DISCREPANCY_SUMMARY:
            return self._build_discrepancy_prompt(language, context, **kwargs)
        elif prompt_type == PromptType.BANK_DRAFT:
            return self._build_bank_draft_prompt(language, context, **kwargs)
        elif prompt_type == PromptType.AMENDMENT_DRAFT:
            return self._build_amendment_prompt(language, context, **kwargs)
        elif prompt_type == PromptType.CHAT:
            return self._build_chat_prompt(language, context, **kwargs)
        else:
            raise ValueError(f"Unknown prompt type: {prompt_type}")

    def _build_discrepancy_prompt(
        self,
        language: PromptLanguage,
        context: Dict[str, Any],
        **kwargs
    ) -> str:
        """Build discrepancy analysis prompt"""

        lc_id = context.get("lc_id", "")
        discrepancies = context.get("discrepancies", [])
        include_recommendations = kwargs.get("include_recommendations", True)
        analysis_depth = kwargs.get("analysis_depth", "standard")

        if language == PromptLanguage.ENGLISH:
            prompt = f"""
Please analyze the following discrepancies for Letter of Credit {lc_id}:

DISCREPANCY DETAILS:
"""
            for i, disc in enumerate(discrepancies, 1):
                prompt += f"""
{i}. Field: {disc.get('field_name', 'Unknown')}
   Expected: {disc.get('expected_value', 'Not specified')}
   Actual: {disc.get('actual_value', 'Not specified')}
   Severity: {disc.get('severity', 'Unknown')}
"""

            prompt += f"""
ANALYSIS REQUIREMENTS:
- Provide {analysis_depth} analysis of each discrepancy
- Assess compliance with UCP 600 guidelines
- Evaluate potential impact on LC acceptance
- Rate the overall risk level (Low/Medium/High)
"""

            if include_recommendations:
                prompt += """
- Include specific recommendations for resolution
- Suggest next steps for each discrepancy
- Provide timeline for corrective actions
"""

            prompt += """
Please structure your response with clear sections for each discrepancy and provide an executive summary at the end.
"""

        elif language == PromptLanguage.BANGLA:
            prompt = f"""
লেটার অব ক্রেডিট {lc_id} এর নিম্নলিখিত অসঙ্গতিগুলি বিশ্লেষণ করুন:

অসঙ্গতির বিবরণ:
"""
            for i, disc in enumerate(discrepancies, 1):
                prompt += f"""
{i}. ক্ষেত্র: {disc.get('field_name', 'অজানা')}
   প্রত্যাশিত: {disc.get('expected_value', 'নির্দিষ্ট নয়')}
   প্রকৃত: {disc.get('actual_value', 'নির্দিষ্ট নয়')}
   তীব্রতা: {disc.get('severity', 'অজানা')}
"""

            prompt += f"""
বিশ্লেষণের প্রয়োজনীয়তা:
- প্রতিটি অসঙ্গতির {analysis_depth} বিশ্লেষণ প্রদান করুন
- UCP 600 নির্দেশিকার সাথে সম্মতি মূল্যায়ন করুন
- এলসি গ্রহণযোগ্যতার উপর সম্ভাব্য প্রভাব মূল্যায়ন করুন
- সামগ্রিক ঝুঁকির স্তর রেটিং করুন (নিম্ন/মধ্যম/উচ্চ)
"""

            if include_recommendations:
                prompt += """
- সমাধানের জন্য নির্দিষ্ট সুপারিশ অন্তর্ভুক্ত করুন
- প্রতিটি অসঙ্গতির জন্য পরবর্তী পদক্ষেপ সুপারিশ করুন
- সংশোধনমূলক ব্যবস্থার জন্য সময়সীমা প্রদান করুন
"""

            prompt += """
অনুগ্রহ করে প্রতিটি অসঙ্গতির জন্য স্পষ্ট বিভাগ সহ আপনার প্রতিক্রিয়া কাঠামো করুন এবং শেষে একটি নির্বাহী সারাংশ প্রদান করুন।
"""

        return prompt

    def _build_bank_draft_prompt(
        self,
        language: PromptLanguage,
        context: Dict[str, Any],
        **kwargs
    ) -> str:
        """Build bank draft prompt"""

        lc_id = context.get("lc_id", "")
        discrepancies = context.get("discrepancies", [])
        recipient_bank = kwargs.get("recipient_bank", "")
        notification_type = kwargs.get("notification_type", "discrepancy_advice")
        include_legal_disclaimer = kwargs.get("include_legal_disclaimer", False)

        if language == PromptLanguage.ENGLISH:
            prompt = f"""
Draft a formal banking correspondence for {notification_type.replace('_', ' ').title()} regarding Letter of Credit {lc_id}.

CORRESPONDENCE DETAILS:
- Recipient Bank: {recipient_bank}
- LC Reference: {lc_id}
- Type: {notification_type.replace('_', ' ').title()}

DISCREPANCIES TO ADDRESS:
"""
            for i, disc in enumerate(discrepancies, 1):
                prompt += f"""
{i}. {disc.get('field_name', 'Unknown Field')}
   Expected: {disc.get('expected_value', 'Not specified')}
   Found: {disc.get('actual_value', 'Not specified')}
   Severity: {disc.get('severity', 'Unknown')}
"""

            prompt += """
FORMATTING REQUIREMENTS:
- Use professional banking language
- Follow SWIFT messaging conventions
- Include proper bank identification
- Maintain formal business tone
- Reference applicable UCP 600 articles
"""

            if include_legal_disclaimer:
                prompt += """
- Include appropriate legal disclaimers
- Add compliance statements as needed
"""

            prompt += """
Please format as a complete business letter with proper headers, body, and closing.
"""

        elif language == PromptLanguage.BANGLA:
            prompt = f"""
লেটার অব ক্রেডিট {lc_id} সম্পর্কিত {notification_type.replace('_', ' ')} এর জন্য একটি আনুষ্ঠানিক ব্যাংকিং চিঠিপত্র খসড়া করুন।

চিঠিপত্রের বিবরণ:
- প্রাপক ব্যাংক: {recipient_bank}
- এলসি রেফারেন্স: {lc_id}
- ধরন: {notification_type.replace('_', ' ')}

সমাধান করার জন্য অসঙ্গতি:
"""
            for i, disc in enumerate(discrepancies, 1):
                prompt += f"""
{i}. {disc.get('field_name', 'অজানা ক্ষেত্র')}
   প্রত্যাশিত: {disc.get('expected_value', 'নির্দিষ্ট নয়')}
   পাওয়া গেছে: {disc.get('actual_value', 'নির্দিষ্ট নয়')}
   তীব্রতা: {disc.get('severity', 'অজানা')}
"""

            prompt += """
ফর্ম্যাটিং প্রয়োজনীয়তা:
- পেশাদার ব্যাংকিং ভাষা ব্যবহার করুন
- SWIFT বার্তা নিয়মাবলী অনুসরণ করুন
- যথাযথ ব্যাংক সনাক্তকরণ অন্তর্ভুক্ত করুন
- আনুষ্ঠানিক ব্যবসায়িক টোন বজায় রাখুন
"""

            prompt += """
অনুগ্রহ করে যথাযথ হেডার, বডি এবং ক্লোজিং সহ একটি সম্পূর্ণ ব্যবসায়িক চিঠি হিসেবে ফর্ম্যাট করুন।
"""

        return prompt

    def _build_amendment_prompt(
        self,
        language: PromptLanguage,
        context: Dict[str, Any],
        **kwargs
    ) -> str:
        """Build amendment draft prompt"""

        lc_id = context.get("lc_id", "")
        discrepancies = context.get("discrepancies", [])
        amendment_type = kwargs.get("amendment_type", "partial")
        custom_instructions = kwargs.get("custom_instructions", "")
        include_rationale = kwargs.get("include_rationale", True)
        format_type = kwargs.get("format", "swift_mt707")

        if language == PromptLanguage.ENGLISH:
            prompt = f"""
Draft a {amendment_type} amendment for Letter of Credit {lc_id} to address the following discrepancies:

DISCREPANCIES TO RESOLVE:
"""
            for i, disc in enumerate(discrepancies, 1):
                prompt += f"""
{i}. Field: {disc.get('field_name', 'Unknown')}
   Current Value: {disc.get('actual_value', 'Not specified')}
   Required Value: {disc.get('expected_value', 'Not specified')}
   Severity: {disc.get('severity', 'Unknown')}
"""

            prompt += f"""
AMENDMENT SPECIFICATIONS:
- Amendment Type: {amendment_type.title()}
- Format: {format_type.upper()}
- LC Reference: {lc_id}
"""

            if custom_instructions:
                prompt += f"""
- Special Instructions: {custom_instructions}
"""

            prompt += """
REQUIREMENTS:
- Follow SWIFT MT707 field structure
- Use precise, unambiguous language
- Include proper field references
- Maintain UCP 600 compliance
- Provide clear before/after values
"""

            if include_rationale:
                prompt += """
- Include rationale for each amendment
- Explain the business justification
- Reference applicable regulations
"""

            prompt += """
Please format the amendment following standard banking practices with proper field sequencing and clear instructions.
"""

        elif language == PromptLanguage.BANGLA:
            prompt = f"""
নিম্নলিখিত অসঙ্গতিগুলি সমাধানের জন্য লেটার অব ক্রেডিট {lc_id} এর একটি {amendment_type} সংশোধনী খসড়া করুন:

সমাধানের জন্য অসঙ্গতি:
"""
            for i, disc in enumerate(discrepancies, 1):
                prompt += f"""
{i}. ক্ষেত্র: {disc.get('field_name', 'অজানা')}
   বর্তমান মান: {disc.get('actual_value', 'নির্দিষ্ট নয়')}
   প্রয়োজনীয় মান: {disc.get('expected_value', 'নির্দিষ্ট নয়')}
   তীব্রতা: {disc.get('severity', 'অজানা')}
"""

            prompt += f"""
সংশোধনী নির্দিষ্টকরণ:
- সংশোধনীর ধরন: {amendment_type}
- ফর্ম্যাট: {format_type.upper()}
- এলসি রেফারেন্স: {lc_id}
"""

            if custom_instructions:
                prompt += f"""
- বিশেষ নির্দেশাবলী: {custom_instructions}
"""

            prompt += """
প্রয়োজনীয়তা:
- SWIFT MT707 ক্ষেত্র কাঠামো অনুসরণ করুন
- নির্ভুল, দ্ব্যর্থহীন ভাষা ব্যবহার করুন
- যথাযথ ক্ষেত্র রেফারেন্স অন্তর্ভুক্ত করুন
- UCP 600 সম্মতি বজায় রাখুন
- স্পষ্ট আগে/পরে মান প্রদান করুন
"""

            if include_rationale:
                prompt += """
- প্রতিটি সংশোধনীর জন্য যুক্তি অন্তর্ভুক্ত করুন
- ব্যবসায়িক যুক্তি ব্যাখ্যা করুন
- প্রযোজ্য নিয়মাবলী রেফারেন্স করুন
"""

            prompt += """
অনুগ্রহ করে যথাযথ ক্ষেত্র ক্রম এবং স্পষ্ট নির্দেশাবলী সহ মানক ব্যাংকিং অনুশীলন অনুসরণ করে সংশোধনী ফর্ম্যাট করুন।
"""

        return prompt

    def _build_chat_prompt(
        self,
        language: PromptLanguage,
        context: Dict[str, Any],
        **kwargs
    ) -> str:
        """Build chat prompt"""

        message = context.get("message", "")
        lc_id = context.get("lc_id")
        conversation_history = context.get("context", {}).get("conversation_history", [])

        if language == PromptLanguage.ENGLISH:
            prompt = f"User message: {message}\n"

            if lc_id:
                prompt += f"Context: Discussion related to LC {lc_id}\n"

            if conversation_history:
                prompt += "\nConversation history:\n"
                for msg in conversation_history[-3:]:  # Last 3 messages for context
                    sender = msg.get("sender", "unknown")
                    content = msg.get("content", "")
                    prompt += f"{sender.capitalize()}: {content}\n"

            prompt += "\nPlease provide a helpful response focused on trade finance topics."

        elif language == PromptLanguage.BANGLA:
            prompt = f"ব্যবহারকারীর বার্তা: {message}\n"

            if lc_id:
                prompt += f"প্রসঙ্গ: এলসি {lc_id} সম্পর্কিত আলোচনা\n"

            if conversation_history:
                prompt += "\nকথোপকথনের ইতিহাস:\n"
                for msg in conversation_history[-3:]:
                    sender = msg.get("sender", "অজানা")
                    content = msg.get("content", "")
                    prompt += f"{sender}: {content}\n"

            prompt += "\nঅনুগ্রহ করে ট্রেড ফাইন্যান্স বিষয়ের উপর ফোকাস করে একটি সহায়ক প্রতিক্রিয়া প্রদান করুন।"

        return prompt


class ComplianceGuardrails:
    """Compliance guardrails and validation for AI responses"""

    @staticmethod
    def validate_trade_finance_content(content: str) -> bool:
        """Validate that content is trade finance related"""
        trade_finance_keywords = [
            "letter of credit", "lc", "documentary credit", "ucp", "swift",
            "discrepancy", "amendment", "beneficiary", "applicant", "issuing bank",
            "advising bank", "confirming bank", "trade finance", "export", "import",
            "bill of lading", "invoice", "certificate", "incoterms", "isbp"
        ]

        content_lower = content.lower()
        return any(keyword in content_lower for keyword in trade_finance_keywords)

    @staticmethod
    def filter_sensitive_information(content: str) -> str:
        """Filter out sensitive information from AI responses"""
        import re

        # Filter account numbers
        content = re.sub(r'\b\d{8,20}\b', '[ACCOUNT_NUMBER_REDACTED]', content)

        # Filter SWIFT codes (but keep generic ones)
        content = re.sub(r'\b[A-Z]{4}[A-Z0-9]{2}[A-Z0-9]{3}\b', '[SWIFT_CODE_REDACTED]', content)

        # Filter potential SSNs
        content = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', content)

        # Filter credit card numbers
        content = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[CARD_NUMBER_REDACTED]', content)

        return content

    @staticmethod
    def add_compliance_footer(content: str, language: PromptLanguage) -> str:
        """Add compliance footer to AI responses"""
        footers = {
            PromptLanguage.ENGLISH: """

---
COMPLIANCE NOTICE: This analysis is generated by AI and should be reviewed by qualified trade finance professionals. Please consult with your bank's trade finance department for official guidance. This information is for educational purposes only and does not constitute legal or financial advice.
""",
            PromptLanguage.BANGLA: """

---
সম্মতি বিজ্ঞপ্তি: এই বিশ্লেষণ AI দ্বারা উত্পন্ন এবং যোগ্য ট্রেড ফাইন্যান্স পেশাদারদের দ্বারা পর্যালোচনা করা উচিত। অফিসিয়াল নির্দেশনার জন্য অনুগ্রহ করে আপনার ব্যাংকের ট্রেড ফাইন্যান্স বিভাগের সাথে পরামর্শ করুন। এই তথ্য শুধুমাত্র শিক্ষামূলক উদ্দেশ্যে এবং আইনি বা আর্থিক পরামর্শ গঠন করে না।
"""
        }

        return content + footers.get(language, footers[PromptLanguage.ENGLISH])


# Prompt templates for quick access
PROMPT_TEMPLATES = {
    "discrepancy_summary_en": """Analyze the following Letter of Credit discrepancies:

{discrepancy_list}

Provide:
1. Detailed analysis of each discrepancy
2. UCP 600 compliance assessment
3. Risk evaluation and recommendations
4. Next steps for resolution

Format your response with clear sections and executive summary.""",

    "bank_draft_en": """Draft a professional banking correspondence:

Type: {notification_type}
LC: {lc_id}
Recipient: {recipient_bank}

Discrepancies:
{discrepancy_list}

Use formal banking language and SWIFT conventions.""",

    "amendment_draft_en": """Draft LC amendment for {lc_id}:

Type: {amendment_type}
Format: SWIFT MT707

Required changes:
{change_list}

Include proper field references and clear instructions."""
}


# Export the main builder class
__all__ = [
    'AIPromptBuilder',
    'PromptLanguage',
    'PromptType',
    'ComplianceGuardrails',
    'PROMPT_TEMPLATES'
]