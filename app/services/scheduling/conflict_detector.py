from typing import Dict, Any, List
from datetime import datetime


class ConflictDetectionService:
    """Service responsible for detecting and resolving scheduling conflicts"""
    
    def detect_time_conflicts(self, time_slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect conflicts between time slots"""
        conflicts = []
        
        for i, slot1 in enumerate(time_slots):
            for j, slot2 in enumerate(time_slots[i+1:], i+1):
                if self._times_overlap(slot1, slot2):
                    conflicts.append({
                        "type": "time_overlap",
                        "description": f"Conflict between '{slot1['taskTitle']}' and '{slot2['taskTitle']}'",
                        "slots": [i, j],
                        "severity": self._calculate_conflict_severity(slot1, slot2),
                        "suggestions": self._generate_conflict_suggestions(slot1, slot2)
                    })
        
        return conflicts
    
    def resolve_conflicts(self, conflicts: List[Dict[str, Any]], 
                         time_slots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate conflict resolution suggestions"""
        if not conflicts:
            return {"conflicts_resolved": 0, "suggestions": []}
        
        resolution_suggestions = []
        
        for conflict in conflicts:
            slot_indices = conflict["slots"]
            slot1, slot2 = time_slots[slot_indices[0]], time_slots[slot_indices[1]]
            
            # Generate specific resolution strategies
            if conflict["severity"] == "high":
                # High priority conflicts need immediate attention
                resolution_suggestions.extend([
                    f"URGENT: Reschedule '{slot2['taskTitle']}' to avoid conflict with '{slot1['taskTitle']}'",
                    f"Consider reducing duration of '{slot1['taskTitle']}' from {slot1.get('duration', 60)} to {max(30, slot1.get('duration', 60) - 30)} minutes"
                ])
            else:
                # Medium/low conflicts can have flexible solutions
                resolution_suggestions.extend([
                    f"Move '{slot2['taskTitle']}' to next available time slot",
                    f"Check if '{slot1['taskTitle']}' can start 15-30 minutes later"
                ])
        
        return {
            "conflicts_resolved": len(conflicts),
            "suggestions": resolution_suggestions,
            "total_affected_tasks": len(set([idx for conflict in conflicts for idx in conflict["slots"]]))
        }
    
    def validate_schedule(self, time_slots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate entire schedule for conflicts and issues"""
        conflicts = self.detect_time_conflicts(time_slots)
        
        # Additional validations
        issues = []
        
        # Check for unrealistic time gaps
        sorted_slots = sorted(time_slots, key=lambda x: x.get("startTime", "00:00"))
        for i in range(len(sorted_slots) - 1):
            current_end = sorted_slots[i].get("endTime", "00:00")
            next_start = sorted_slots[i + 1].get("startTime", "00:00")
            
            gap = self._calculate_time_gap(current_end, next_start)
            if gap < 5:  # Less than 5 minutes between tasks
                issues.append({
                    "type": "insufficient_break",
                    "message": f"Only {gap} minutes between '{sorted_slots[i]['taskTitle']}' and '{sorted_slots[i+1]['taskTitle']}'",
                    "severity": "medium"
                })
        
        # Check for very long working blocks
        for slot in time_slots:
            duration = slot.get("duration", 60)
            if duration > 180:  # More than 3 hours
                issues.append({
                    "type": "long_work_block",
                    "message": f"'{slot['taskTitle']}' is scheduled for {duration} minutes - consider breaking it down",
                    "severity": "low"
                })
        
        return {
            "is_valid": len(conflicts) == 0 and len(issues) == 0,
            "conflicts": conflicts,
            "issues": issues,
            "recommendations": self._generate_schedule_recommendations(time_slots, conflicts, issues)
        }
    
    def _times_overlap(self, slot1: Dict[str, Any], slot2: Dict[str, Any]) -> bool:
        """Check if two time slots overlap"""
        try:
            start1 = datetime.strptime(slot1.get("startTime", "00:00"), "%H:%M")
            end1 = datetime.strptime(slot1.get("endTime", "00:00"), "%H:%M") 
            start2 = datetime.strptime(slot2.get("startTime", "00:00"), "%H:%M")
            end2 = datetime.strptime(slot2.get("endTime", "00:00"), "%H:%M")
            
            return not (end1 <= start2 or end2 <= start1)
        except ValueError:
            return False
    
    def _calculate_conflict_severity(self, slot1: Dict[str, Any], slot2: Dict[str, Any]) -> str:
        """Calculate severity of conflict based on task priorities and types"""
        priority1 = slot1.get("priority", "medium")
        priority2 = slot2.get("priority", "medium")
        
        priority_values = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
        
        max_priority = max(priority_values.get(priority1, 2), priority_values.get(priority2, 2))
        
        if max_priority >= 4:
            return "high"
        elif max_priority >= 3:
            return "medium"
        else:
            return "low"
    
    def _generate_conflict_suggestions(self, slot1: Dict[str, Any], slot2: Dict[str, Any]) -> List[str]:
        """Generate specific suggestions for resolving conflicts"""
        suggestions = []
        
        # Priority-based suggestions
        priority1 = slot1.get("priority", "medium")
        priority2 = slot2.get("priority", "medium")
        
        if priority1 == "urgent" and priority2 != "urgent":
            suggestions.append(f"Keep '{slot1['taskTitle']}' as scheduled, move '{slot2['taskTitle']}'")
        elif priority2 == "urgent" and priority1 != "urgent":
            suggestions.append(f"Keep '{slot2['taskTitle']}' as scheduled, move '{slot1['taskTitle']}'")
        
        # Flexibility-based suggestions
        flexibility1 = slot1.get("flexibility", "flexible")
        flexibility2 = slot2.get("flexibility", "flexible")
        
        if flexibility1 == "flexible" and flexibility2 == "fixed":
            suggestions.append(f"'{slot1['taskTitle']}' can be rescheduled more easily")
        elif flexibility2 == "flexible" and flexibility1 == "fixed":
            suggestions.append(f"'{slot2['taskTitle']}' can be rescheduled more easily")
        
        # Duration-based suggestions
        duration1 = slot1.get("duration", 60)
        duration2 = slot2.get("duration", 60)
        
        if duration1 > duration2:
            suggestions.append(f"Consider shortening '{slot1['taskTitle']}' by {min(30, duration1 - duration2)} minutes")
        else:
            suggestions.append(f"Consider shortening '{slot2['taskTitle']}' by {min(30, duration2 - duration1)} minutes")
        
        return suggestions or [
            f"Move '{slot2['taskTitle']}' to later time",
            f"Reduce duration of '{slot1['taskTitle']}'"
        ]
    
    def _calculate_time_gap(self, end_time: str, start_time: str) -> int:
        """Calculate gap in minutes between two times"""
        try:
            end = datetime.strptime(end_time, "%H:%M")
            start = datetime.strptime(start_time, "%H:%M")
            
            # Handle next day case
            if start < end:
                start = start.replace(day=start.day + 1)
            
            gap = (start - end).total_seconds() / 60
            return int(gap)
        except ValueError:
            return 0
    
    def _generate_schedule_recommendations(self, time_slots: List[Dict[str, Any]], 
                                         conflicts: List[Dict[str, Any]], 
                                         issues: List[Dict[str, Any]]) -> List[str]:
        """Generate overall schedule recommendations"""
        recommendations = []
        
        if conflicts:
            recommendations.append(f"Resolve {len(conflicts)} scheduling conflicts before finalizing")
        
        if issues:
            high_priority_issues = [i for i in issues if i.get("severity") == "high"]
            if high_priority_issues:
                recommendations.append(f"Address {len(high_priority_issues)} high-priority scheduling issues")
        
        # Check for work-life balance
        work_tasks = [s for s in time_slots if s.get("category") in ["work", "meeting", "deep_work"]]
        if len(work_tasks) > 6:
            recommendations.append("Consider reducing work tasks to maintain work-life balance")
        
        # Check for break times
        total_work_time = sum([s.get("duration", 60) for s in work_tasks])
        if total_work_time > 480:  # More than 8 hours
            recommendations.append("Schedule breaks between long work sessions")
        
        return recommendations