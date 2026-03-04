from typing import List, Dict, Optional
from backend.schemas.split import SplitRequest, SplitType
from decimal import Decimal, ROUND_HALF_UP

class SplitCalculator:
    def calculate_split(self, total_amount: float, request: SplitRequest, items: Optional[List[dict]] = None) -> List[dict]:
        """
        Calculates how much each user owes based on the split type.
        Ensures Sum(user_shares) == total
        Addresses rounding safety and precision handling using Decimal.
        """
        total_dec = Decimal(str(total_amount))
        users = request.users
        n_users = len(users)
        
        if n_users == 0:
            raise ValueError("At least one user is required for splitting.")
            
        shares = []
        
        if request.split_type == SplitType.EQUAL:
            # Divide equally, put remainder on the first user
            base_share = (total_dec / Decimal(str(n_users))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            total_allocated = base_share * Decimal(str(n_users))
            difference = total_dec - total_allocated
            
            for i, user in enumerate(users):
                amount = base_share
                if i == 0:
                    amount += difference # Distribute penny logic
                shares.append({"user_name": user, "share_amount": float(amount)})
                
        elif request.split_type == SplitType.CUSTOM:
            # Custom splits provided directly (e.g. percentages or exact amounts)
            # Normalizing to exact amounts if they just represent weights, 
            # assuming exact amounts here as requested manually.
            custom_shares = request.custom_shares
            total_custom = sum(Decimal(str(v)) for v in custom_shares.values())
            
            if total_custom != total_dec:
                 raise ValueError(f"Sum of custom shares ({total_custom}) does not equal total amount ({total_dec}).")
                 
            for user in users:
                amt = Decimal(str(custom_shares.get(user, 0)))
                shares.append({"user_name": user, "share_amount": float(amt)})
                
        elif request.split_type == SplitType.PROPORTIONAL:
            # Proportional relative to some weights passed via custom shares
            # For this we treat custom_shares as weights mapping.
            weights = request.custom_shares
            total_weight = sum(Decimal(str(w)) for w in weights.values())
            
            if total_weight == Decimal("0.0"):
                raise ValueError("Total weight for proportional split cannot be zero.")
                
            allocated = Decimal("0.0")
            
            for i, user in enumerate(users):
                weight = Decimal(str(weights.get(user, 0)))
                share = (total_dec * (weight / total_weight)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
                if i == n_users - 1:
                    # Last user gets remainder
                    share = total_dec - allocated
                allocated += share
                shares.append({"user_name": user, "share_amount": float(share)})
                
        elif request.split_type == SplitType.ITEM_BASED:
            # Items need to be provided
            if not items:
                raise ValueError("Line items are required for an item-based split.")
                
            assignments = request.item_assignments # Mapping item_id to list of users sharing it
            
            user_totals = {user: Decimal("0.0") for user in users}
            
            # Map items list to dictionary for O(1) fetch
            item_map = {item['id']: Decimal(str(item['amount'])) for item in items}
            
            allocated_from_items = Decimal("0.0")
            for item_id, assigned_users in assignments.items():
                if int(item_id) not in item_map:
                    continue # Skip invalid items
                    
                item_amt = item_map[int(item_id)]
                allocated_from_items += item_amt
                
                n_assigned = len(assigned_users)
                if n_assigned == 0:
                    continue
                    
                base_share = (item_amt / Decimal(str(n_assigned))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                item_allocated = base_share * Decimal(str(n_assigned))
                diff = item_amt - item_allocated
                
                for i, u in enumerate(assigned_users):
                    if u in user_totals:
                        amt = base_share + (diff if i == 0 else Decimal("0.0"))
                        user_totals[u] += amt
            
            # Subtotal mismatch from Total Amount (Taxes/Tips)
            remaining_total = total_dec - allocated_from_items
            
            # Distribute the remaining tax/tip proportionally to what users already owe
            # Or equally if allocating failed. We distribute proportionally.
            if allocated_from_items > Decimal("0.0") and remaining_total != Decimal("0.0"):
                for user in users:
                    prop = user_totals[user] / allocated_from_items
                    extra = (remaining_total * prop).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    user_totals[user] += extra
                    
                # Fix rounding issues across all users for total summation
                final_sum = sum(user_totals.values())
                diff = total_dec - final_sum
                # Give diff to first user
                if len(users) > 0:
                    user_totals[users[0]] += diff
            elif remaining_total != Decimal("0.0"):
                 # Distribute equally if no items were mapped or items sum to 0
                 base_extra = (remaining_total / Decimal(str(n_users))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                 for i, u in enumerate(users):
                     if u in user_totals:
                         user_totals[u] += base_extra + (remaining_total - (base_extra * n_users) if i == 0 else Decimal("0.0"))

            for user in users:
                shares.append({"user_name": user, "share_amount": float(user_totals[user])})

        return shares
