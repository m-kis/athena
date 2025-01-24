from typing import List, Dict

# src/agents/security/prompt_generator.py
class SecurityPromptGenerator:
    def generate_prompt(self, issues: List[Dict]) -> str:
        """Generate security analysis prompt"""
        issue_types = set(issue['type'] for issue in issues)
        
        sections = ["Analyze the security issues found in the logs with focus on:"]
        
        type_prompts = {
            'auth_failure': "Authentication failure patterns and potential breach attempts",
            'injection': "Injection attempts and their potential impact",
            'suspicious_ip': "Suspicious IP activity patterns",
            'privilege_escalation': "Privilege escalation attempts",
            'brute_force': "Brute force attack patterns",
            'malware': "Malware and malicious activity indicators"
        }
        
        for i, (issue_type, prompt) in enumerate(type_prompts.items(), 1):
            if issue_type in issue_types:
                sections.append(f"{i}. {prompt}")

        sections.extend([
            "\nFor each issue type, provide:",
            "1. Severity assessment",
            "2. Potential impact",
            "3. Specific mitigation steps",
            "4. Long-term security recommendations"
        ])

        return "\n".join(sections)

    def extract_recommendations(self, analysis: str) -> List[str]:
        """Extract recommendations from analysis"""
        recommendations = []
        in_recommendations = False
        
        for line in analysis.split('\n'):
            if 'recommend' in line.lower() or 'mitigation' in line.lower():
                in_recommendations = True
            elif in_recommendations and line.strip():
                if line.startswith(('•', '-', '*', '1.', '2.', '3.')):
                    recommendations.append(line.strip('•').strip('*').strip('- ').strip())
                    
        return recommendations