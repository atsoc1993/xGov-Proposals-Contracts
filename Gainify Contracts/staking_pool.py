from algopy import (
    ARC4Contract, UInt64,
    gtxn, String,
    Application, Global,
    Txn, itxn,
    Account, subroutine,
    op, TransactionType,
    BoxMap, urange,
    BigUInt, ensure_budget,
    OpUpFeeSource
)
from algopy.arc4 import (
    abimethod,
    Struct,
    Address,
    abi_call,
    DynamicArray,
    Bool
)
from algopy.arc4 import UInt64 as arc4UInt64


'''
CREATORS: Leo, Allan, Ulrik
'''


'''
A User's Stake Instance — contains info about how much they have staked
, when they staked, their rewards so far, whether they have an NFD boost
toggled, and their box index.
'''
class UserStake(Struct):
    stake_amount: arc4UInt64
    stake_time: arc4UInt64
    reward_asset: arc4UInt64
    reward_supplement: arc4UInt64
    last_counter: arc4UInt64
    boosted: Bool
    boost_amount: arc4UInt64
    
class StakeActivity(Struct):
    total_stake_amount: arc4UInt64
    change_time: arc4UInt64
    
    
class GainifyStakingPool(ARC4Contract):
    def __init__(self) -> None:
        '''Global States and Box Mappings'''
        self.MASTER_APP_ID = Application()
        self.MASTER_APP_ADDRESS = Account()
        self.FEE_ADDRESS = Account()
        self.STAKE_ASSET = UInt64()
        
        self.STAKED_ASSET_AMOUNT = UInt64(0)
    
        self.REWARD_ASSET = UInt64()
        self.REWARD_ASSET_AMOUNT = UInt64()
        self.REWARD_RATE_ASSET = UInt64()
        self.ASSET_SCALE_FACTOR = UInt64()

        self.SUPPLEMENTAL_REWARD_ASSET = UInt64()
        self.SUPPLEMENTAL_REWARD_ASSET_AMOUNT = UInt64()
        self.SUPPLEMENTAL_REWARD_RATE = UInt64()
        self.SUPPLEMENTAL_ASSET_SCALE_FACTOR = UInt64()

        self.WEBSITE_LINK = String()
        self.DISCORD_LINK = String()
        self.X_LINK = String()
        
        self.BOOST_TOGGLED = bool()
        self.POOL_START_TIME = UInt64(0)
        self.POOL_LENGTH = UInt64(0)
        

        self.STAKE_ACTIVITY_COUNTER = arc4UInt64(0)

        self.STAKE_ACTIVITY = BoxMap(
            arc4UInt64,
            DynamicArray[StakeActivity],
            key_prefix="",
        )

        self.USER_STAKE_BOX = BoxMap(
            Address,
            UserStake,
            key_prefix="",
        )

    @abimethod
    def opt_into_assets(self, 
        STAKE_ASSET: UInt64, 
        reward_asset: UInt64, 
        supplemental_asset: UInt64,
        supplemental_asset_amount: UInt64,
        mbr_payment: gtxn.PaymentTransaction
    ) -> None:
        '''
        This method is called from the master gainify contract to prepare 
        staking pool instance to accept stake, primary reward, 
        and secondary reward assets
        '''
        assert Txn.sender == Global.creator_address
        assert mbr_payment.amount >= 2000
        assert STAKE_ASSET != 0 and STAKE_ASSET != 31566704
        
        itxn.AssetTransfer(
            asset_receiver=Global.current_application_address,
            xfer_asset=STAKE_ASSET,
            fee=Global.min_txn_fee
        ).submit()
        
        if reward_asset != 0:
            itxn.AssetTransfer(
                asset_receiver=Global.current_application_address,
                xfer_asset=reward_asset,
                fee=Global.min_txn_fee
            ).submit()
            
        if supplemental_asset !=0 and supplemental_asset_amount != 0:
            itxn.AssetTransfer(
                asset_receiver=Global.current_application_address,
                xfer_asset=supplemental_asset,
                fee=Global.min_txn_fee
            ).submit()
        

    @subroutine
    def determine_assets_and_amounts(
        self,
        reward_asset_payment: gtxn.Transaction,
        supplemental_asset_payment: gtxn.Transaction, 
    ) -> tuple[UInt64, UInt64, UInt64, UInt64]:
        '''Determines the primary and secondary reward asset for this staking pool'''
        reward_asset = UInt64(0)
        reward_asset_amount = UInt64(0)
        supplemental_reward_asset = UInt64(0)
        supplemental_reward_asset_amount = UInt64(0)

        if reward_asset_payment.type == TransactionType.Payment:
            reward_asset = UInt64(0)
            reward_asset_amount = reward_asset_payment.amount
            assert reward_asset_payment.receiver == Global.current_application_address

        elif reward_asset_payment.type == TransactionType.AssetTransfer:
            reward_asset = reward_asset_payment.xfer_asset.id
            reward_asset_amount = reward_asset_payment.asset_amount
            assert reward_asset_payment.asset_receiver == Global.current_application_address
        
        if supplemental_asset_payment.type == TransactionType.Payment:
            supplemental_reward_asset = UInt64(0)
            supplemental_reward_asset_amount = supplemental_asset_payment.amount
            assert supplemental_asset_payment.receiver == Global.current_application_address

        elif supplemental_asset_payment.type == TransactionType.AssetTransfer:
            supplemental_reward_asset = supplemental_asset_payment.xfer_asset.id
            supplemental_reward_asset_amount = supplemental_asset_payment.asset_amount
            assert supplemental_asset_payment.asset_receiver == Global.current_application_address
            
        return reward_asset, reward_asset_amount, supplemental_reward_asset, supplemental_reward_asset_amount
            
            
    @abimethod
    def initialize_staking_pool(self,
        pool_length: UInt64,
        STAKE_ASSET: UInt64,
        reward_asset_payment: gtxn.Transaction,
        supplemental_asset_payment: gtxn.Transaction,
        website_link: String,
        discord_link: String,
        x_link: String,
        boost_toggled: bool,
        FEE_ADDRESS: Account,
        master_app: Application
    ) -> None:
        '''Initializes the staking pool with various parameters'''
        self.POOL_LENGTH = pool_length
        self.POOL_START_TIME = Global.latest_timestamp
        self.FEE_ADDRESS = FEE_ADDRESS
        assert Txn.sender == Global.creator_address
        assert 259_200 <= pool_length <= 15_552_000
        
        reward_asset, reward_asset_amount, supplemental_reward_asset, supplemental_reward_asset_amount = self.determine_assets_and_amounts(
            reward_asset_payment,
            supplemental_asset_payment, 
        )

        assert reward_asset != supplemental_reward_asset
        
        self.MASTER_APP_ID = master_app
        self.MASTER_APP_ADDRESS = master_app.address
        
        self.STAKE_ASSET = STAKE_ASSET

        self.REWARD_ASSET = reward_asset
        self.REWARD_ASSET_AMOUNT = reward_asset_amount
        self.ASSET_SCALE_FACTOR = UInt64((2**64) - 1) // reward_asset_amount
        reward_rates = (op.mulw(reward_asset_amount, self.ASSET_SCALE_FACTOR))
        self.REWARD_RATE_ASSET =  (reward_rates[0] // pool_length) + (reward_rates[1] // pool_length)

        if supplemental_reward_asset_amount != 0:
            self.SUPPLEMENTAL_REWARD_ASSET = supplemental_reward_asset
            self.SUPPLEMENTAL_REWARD_ASSET_AMOUNT = supplemental_reward_asset_amount
            self.SUPPLEMENTAL_ASSET_SCALE_FACTOR = UInt64((2**64) - 1) // supplemental_reward_asset_amount
            self.SUPPLEMENTAL_REWARD_RATE = ((supplemental_reward_asset_amount * self.SUPPLEMENTAL_ASSET_SCALE_FACTOR) // pool_length)

        else:
            self.SUPPLEMENTAL_REWARD_ASSET_AMOUNT = UInt64(0)
            
        self.WEBSITE_LINK = website_link
        self.DISCORD_LINK = discord_link
        self.X_LINK = x_link
        
        self.BOOST_TOGGLED = boost_toggled


    @subroutine
    def calculate_earnings(
        self,
        user_stake_instance: UserStake,
    ) -> UserStake:
        '''Calculates the users current reward and returns their UserStake struct instance with updated rewards information'''
        asset_reward_sum = UInt64(0)
        supplemental_reward_sum = UInt64(0)
        user_amount_at_timestamp = user_stake_instance.stake_amount.native
        user_boost_at_timestamp = user_stake_instance.boost_amount.native
        user_timestamp = user_stake_instance.stake_time.native
        supplemental_reward = UInt64(0)
        
        max_counter_reached = False
        add_one = False
        current_counter = user_stake_instance.last_counter

        last_timestamp = UInt64(0)
        while not max_counter_reached:
            box_activity_for_counter = self.STAKE_ACTIVITY[current_counter].copy()
            for i in urange(box_activity_for_counter.length):

                if add_one == True:
                    j = i + UInt64(1)
                else:
                    j = i

                activity_in_array = box_activity_for_counter[j].copy()
                activity_amount_at_timestamp = activity_in_array.total_stake_amount.native
                activity_timestamp = activity_in_array.change_time.native
                last_timestamp = activity_timestamp

                ensure_budget(3000, OpUpFeeSource.GroupCredit)

                if j + 1 < box_activity_for_counter.length:

                    if j + 1 < box_activity_for_counter.length:
                        next_index = j + 1
                        next_activity_in_array = box_activity_for_counter[next_index].copy()
                        next_time_stamp = next_activity_in_array.change_time.native

                    if j + 1 == box_activity_for_counter.length and arc4UInt64(current_counter.native + 1) in self.STAKE_ACTIVITY:
                        next_activity_in_array = box_activity_for_counter[0].copy()
                        next_time_stamp = next_activity_in_array.change_time.native
                        add_one = True

                    if activity_timestamp >= user_timestamp:
                        time_diff = next_time_stamp - activity_timestamp
                        asset_per_share_reward_rates = BigUInt(self.REWARD_RATE_ASSET) * time_diff
                        asset_per_share_reward_rate = asset_per_share_reward_rates // self.ASSET_SCALE_FACTOR
                        asset_rewards = BigUInt(user_amount_at_timestamp + user_boost_at_timestamp) * asset_per_share_reward_rate
                        asset_reward = op.btoi((asset_rewards // activity_amount_at_timestamp).bytes)
                        asset_reward_sum += asset_reward

                        if self.SUPPLEMENTAL_REWARD_ASSET_AMOUNT != 0:
                            supplemental_per_share_reward_rates = BigUInt(self.SUPPLEMENTAL_REWARD_RATE) * time_diff
                            supplemental_per_share_reward_rate = supplemental_per_share_reward_rates // self.SUPPLEMENTAL_ASSET_SCALE_FACTOR
                            supplemental_rewards = BigUInt(user_amount_at_timestamp + user_boost_at_timestamp) * supplemental_per_share_reward_rate
                            supplemental_reward = op.btoi((supplemental_rewards // activity_amount_at_timestamp).bytes)
                            supplemental_reward_sum += supplemental_reward
                            
            if current_counter == self.STAKE_ACTIVITY_COUNTER:
                max_counter_reached = True
            else:
                current_counter = arc4UInt64(current_counter.native + 1)
                
        user_stake_instance.last_counter = current_counter
        max_time = self.POOL_START_TIME + self.POOL_LENGTH

        if Global.latest_timestamp > max_time:
            time_diff = max_time - last_timestamp
        else:
            time_diff = Global.latest_timestamp - last_timestamp

        asset_per_share_reward_rates = BigUInt(self.REWARD_RATE_ASSET) * time_diff
        asset_per_share_reward_rate = asset_per_share_reward_rates // self.ASSET_SCALE_FACTOR
        
        asset_rewards = BigUInt(user_amount_at_timestamp + user_boost_at_timestamp) * asset_per_share_reward_rate
        asset_reward = op.btoi((asset_rewards // self.STAKED_ASSET_AMOUNT).bytes)
        asset_reward_sum += asset_reward

        if self.SUPPLEMENTAL_REWARD_ASSET_AMOUNT != 0:

            supplemental_per_share_reward_rates = BigUInt(self.SUPPLEMENTAL_REWARD_RATE) * time_diff
            supplemental_per_share_reward_rate = supplemental_per_share_reward_rates // self.SUPPLEMENTAL_ASSET_SCALE_FACTOR
            
            supplemental_rewards = BigUInt(user_amount_at_timestamp + user_boost_at_timestamp) * supplemental_per_share_reward_rate
            
            supplemental_reward = op.btoi((supplemental_rewards // self.STAKED_ASSET_AMOUNT).bytes)
            supplemental_reward_sum += supplemental_reward

        if asset_reward_sum > 0:

            if self.STAKE_ASSET == self.REWARD_ASSET:
                user_stake_instance.stake_amount = arc4UInt64(user_stake_instance.stake_amount.native + asset_reward_sum)
                user_stake_instance.reward_asset = arc4UInt64(0)

            else:
                user_stake_instance.reward_asset = arc4UInt64(user_stake_instance.reward_asset.native + asset_reward_sum)

            user_stake_instance.stake_time = arc4UInt64(Global.latest_timestamp)
            user_stake_instance.last_counter = current_counter
            
        if supplemental_reward_sum > 0:

            if self.STAKE_ASSET == self.SUPPLEMENTAL_REWARD_ASSET:
                user_stake_instance.stake_amount = arc4UInt64(user_stake_instance.stake_amount.native + supplemental_reward_sum)
                user_stake_instance.reward_supplement = arc4UInt64(0)

            else:
                user_stake_instance.reward_supplement = arc4UInt64(user_stake_instance.reward_supplement.native + supplemental_reward_sum)
                
            user_stake_instance.stake_time = arc4UInt64(Global.latest_timestamp)
            user_stake_instance.last_counter = current_counter

        return user_stake_instance.copy()

    
    @abimethod
    def calculate_user_current_earnings(
        self,
        user_stake_instance: UserStake
    ) -> tuple[arc4UInt64, arc4UInt64, arc4UInt64]:
        '''
        This method was exclusively simulated, and used to calculate a user's current earnings
        It is essentially a duplicate of the `calculate_earnings` subroutine but does not 
        modify state and is an abimethod instead of internal subroutine
        '''
        asset_reward_sum = UInt64(0)
        supplemental_reward_sum = UInt64(0)
        user_amount_at_timestamp = user_stake_instance.stake_amount.native
        user_boost_at_timestamp = user_stake_instance.boost_amount.native
        user_timestamp = user_stake_instance.stake_time.native
        supplemental_reward = UInt64(0)
        
        max_counter_reached = False
        add_one = False
        current_counter = user_stake_instance.last_counter

        last_timestamp = UInt64(0)

        while not max_counter_reached:

            box_activity_for_counter = self.STAKE_ACTIVITY[current_counter].copy()
            for i in urange(box_activity_for_counter.length):

                if add_one == True:
                    j = i + UInt64(1)
                else:
                    j = i

                activity_in_array = box_activity_for_counter[j].copy()
                activity_amount_at_timestamp = activity_in_array.total_stake_amount.native
                activity_timestamp = activity_in_array.change_time.native
                last_timestamp = activity_timestamp

                ensure_budget(3000, OpUpFeeSource.GroupCredit)

                if j + 1 <= box_activity_for_counter.length:

                    if j < box_activity_for_counter.length:
                        next_index = j + 1
                        next_activity_in_array = box_activity_for_counter[next_index].copy()
                        next_time_stamp = next_activity_in_array.change_time.native

                    if j == box_activity_for_counter.length and arc4UInt64(current_counter.native + 1) in self.STAKE_ACTIVITY:
                        next_activity_in_array = box_activity_for_counter[0].copy()
                        next_time_stamp = next_activity_in_array.change_time.native
                        add_one = True

                    if activity_timestamp > user_timestamp:
                        time_diff = next_time_stamp - activity_timestamp
                        asset_per_share_reward_rates = BigUInt(self.REWARD_RATE_ASSET) * time_diff
                        asset_per_share_reward_rate = asset_per_share_reward_rates // self.ASSET_SCALE_FACTOR
                        asset_rewards = BigUInt(user_amount_at_timestamp + user_boost_at_timestamp) * asset_per_share_reward_rate
                        asset_reward = op.btoi((asset_rewards // activity_amount_at_timestamp).bytes)
                        asset_reward_sum += asset_reward
                        if self.SUPPLEMENTAL_REWARD_ASSET_AMOUNT != 0:
                            supplemental_per_share_reward_rates = BigUInt(self.SUPPLEMENTAL_REWARD_RATE) * time_diff
                            supplemental_per_share_reward_rate = supplemental_per_share_reward_rates // self.SUPPLEMENTAL_ASSET_SCALE_FACTOR
                            supplemental_rewards = BigUInt(user_amount_at_timestamp + user_boost_at_timestamp) * supplemental_per_share_reward_rate
                            supplemental_reward = op.btoi((supplemental_rewards // activity_amount_at_timestamp).bytes)
                            supplemental_reward_sum += supplemental_reward

            if current_counter == self.STAKE_ACTIVITY_COUNTER:
                max_counter_reached = True
            else:
                current_counter = arc4UInt64(current_counter.native + 1)
             
            
        max_time = self.POOL_START_TIME + self.POOL_LENGTH

        if Global.latest_timestamp > max_time:
            time_diff = max_time - last_timestamp
        else:
            time_diff = Global.latest_timestamp - last_timestamp

        asset_per_share_reward_rates = BigUInt(self.REWARD_RATE_ASSET) * time_diff
        asset_per_share_reward_rate = asset_per_share_reward_rates // self.ASSET_SCALE_FACTOR
        
        asset_rewards = BigUInt(user_amount_at_timestamp + user_boost_at_timestamp) * asset_per_share_reward_rate
        asset_reward = op.btoi((asset_rewards // self.STAKED_ASSET_AMOUNT).bytes)
        asset_reward_sum += asset_reward
        
        if self.SUPPLEMENTAL_REWARD_ASSET_AMOUNT != 0:
            supplemental_per_share_reward_rates = BigUInt(self.SUPPLEMENTAL_REWARD_RATE) * time_diff
            supplemental_per_share_reward_rate = supplemental_per_share_reward_rates // self.SUPPLEMENTAL_ASSET_SCALE_FACTOR
            
            supplemental_rewards = BigUInt(user_amount_at_timestamp + user_boost_at_timestamp) * supplemental_per_share_reward_rate
            
            supplemental_reward = op.btoi((supplemental_rewards // self.STAKED_ASSET_AMOUNT).bytes)
            supplemental_reward_sum += supplemental_reward

        if asset_reward_sum > 0:

            if self.STAKE_ASSET == self.REWARD_ASSET:
                user_stake_instance.stake_amount = arc4UInt64(user_stake_instance.stake_amount.native + asset_reward_sum)
                user_stake_instance.reward_asset = arc4UInt64(0)

            else:
                user_stake_instance.reward_asset = arc4UInt64(user_stake_instance.reward_asset.native + asset_reward_sum)

            user_stake_instance.stake_time = arc4UInt64(Global.latest_timestamp)
            user_stake_instance.last_counter = current_counter
            
        if supplemental_reward_sum > 0:

            if self.STAKE_ASSET == self.SUPPLEMENTAL_REWARD_ASSET:
                user_stake_instance.stake_amount = arc4UInt64(user_stake_instance.stake_amount.native + supplemental_reward_sum)
                user_stake_instance.reward_supplement = arc4UInt64(0)

            else:
                user_stake_instance.reward_supplement = arc4UInt64(user_stake_instance.reward_supplement.native + supplemental_reward_sum)

            user_stake_instance.stake_time = arc4UInt64(Global.latest_timestamp)
            user_stake_instance.last_counter = current_counter
            
        return user_stake_instance.stake_amount, user_stake_instance.reward_asset, user_stake_instance.reward_supplement
    
           
    @subroutine
    def add_stake_activity(
        self,
        stake_change: arc4UInt64,
        increment: bool
    ) -> None:
        '''Document a staking activity into a box for rolling rewards'''

        if Global.latest_timestamp > self.POOL_START_TIME + self.POOL_LENGTH:
            pass

        else:
            if increment == True:
                self.STAKED_ASSET_AMOUNT = self.STAKED_ASSET_AMOUNT + stake_change.native
            else:
                self.STAKED_ASSET_AMOUNT = self.STAKED_ASSET_AMOUNT - stake_change.native 
                
            new_stake_activity = StakeActivity(
                arc4UInt64(self.STAKED_ASSET_AMOUNT),
                arc4UInt64(Global.latest_timestamp)
            )
            
            if self.STAKE_ACTIVITY_COUNTER in self.STAKE_ACTIVITY:

                current_value = self.STAKE_ACTIVITY[self.STAKE_ACTIVITY_COUNTER].copy()

                if current_value.bytes.length == 1010: #CHANGE TO 1008
                    self.STAKE_ACTIVITY_COUNTER = arc4UInt64(self.STAKE_ACTIVITY_COUNTER.native + 1)
                    self.STAKE_ACTIVITY[self.STAKE_ACTIVITY_COUNTER] = DynamicArray(new_stake_activity.copy())
                else:
                    current_value.append(new_stake_activity.copy())
                    self.STAKE_ACTIVITY[self.STAKE_ACTIVITY_COUNTER] = current_value.copy()

            else:
                self.STAKE_ACTIVITY[self.STAKE_ACTIVITY_COUNTER] = DynamicArray(new_stake_activity.copy())

        

    @abimethod
    def add_stake(
        self,
        STAKE_ASSET_axfer: gtxn.AssetTransferTransaction,
        interaction_fee: gtxn.PaymentTransaction,
        mbr_fees: gtxn.PaymentTransaction,
        nfd_app_id: Application,
    ) -> None:
        '''Add an amount of some ASA to stake'''

        end_timestamp = self.POOL_START_TIME + self.POOL_LENGTH

        sent_stake_amount = STAKE_ASSET_axfer.asset_amount

        assert STAKE_ASSET_axfer.xfer_asset.id == self.STAKE_ASSET
        assert sent_stake_amount > 0
        assert STAKE_ASSET_axfer.asset_receiver == Global.current_application_address
        assert interaction_fee.amount == 330_000
        assert interaction_fee.receiver == Global.current_application_address
        assert mbr_fees.receiver == Global.current_application_address
        assert Global.latest_timestamp < end_timestamp

        user_address = Address(Txn.sender)

        itxn.Payment(
            receiver=self.FEE_ADDRESS,
            amount=330_000,
            fee=Global.min_txn_fee
        ).submit()
        
        if user_address not in self.USER_STAKE_BOX:

            assert mbr_fees.amount >= 45_000

            self.USER_STAKE_BOX[user_address] = UserStake(
                arc4UInt64(sent_stake_amount),
                arc4UInt64(Global.latest_timestamp),
                arc4UInt64(0),
                arc4UInt64(0),
                self.STAKE_ACTIVITY_COUNTER,
                Bool(False),
                arc4UInt64(0)
            )

            self._verify_gainify_nfd_ownership_pool(nfd_app_id)
            self.add_stake_activity(arc4UInt64(sent_stake_amount + self.USER_STAKE_BOX[user_address].boost_amount.native), True)


        else:

            assert mbr_fees.amount >= 15_000

            self._verify_gainify_nfd_ownership_pool(nfd_app_id)
            user_stake_instance = self.USER_STAKE_BOX[user_address].copy()
            new_user_stake_instance = self.calculate_earnings(user_stake_instance)
            new_user_stake_instance.stake_amount = arc4UInt64(user_stake_instance.stake_amount.native + sent_stake_amount)

            self.USER_STAKE_BOX[user_address] = new_user_stake_instance.copy()
            self.add_stake_activity(arc4UInt64(sent_stake_amount + (new_user_stake_instance.boost_amount.native)), True)

    @subroutine
    def _verify_gainify_nfd_ownership_pool(
        self,
        nfd_app_id: Application,
    ) -> None:
        '''Call The Gainify Master Contract & Request Verification that the user owns an NFD segment from the project'''
        user_address = Address(Txn.sender)
        
        pass_tx_fee_payment = itxn.Payment(
            receiver=self.MASTER_APP_ADDRESS,
            amount=Global.min_txn_fee,
            fee = Global.min_txn_fee
        )
        
        if nfd_app_id.id != 0:
            result, txn = abi_call[bool](
                '_verify_gainify_nfd_ownership_master(address,application,pay)bool',
                Address(Txn.sender),
                nfd_app_id,
                pass_tx_fee_payment,
                app_id = self.MASTER_APP_ID,
                fee=Global.min_txn_fee
            )
        
        else:
            result = bool(False)
        
        user_stake_instance = self.USER_STAKE_BOX[user_address].copy()
        
        if result != True:
            user_stake_instance.boost_amount = arc4UInt64(0)
            user_stake_instance.boosted = Bool(False)
        else:
            boost_amounts = user_stake_instance.stake_amount.native * 20
            user_stake_instance.boost_amount = arc4UInt64(boost_amounts // 100 )
            user_stake_instance.boosted = Bool(True)
            
        self.USER_STAKE_BOX[user_address] = user_stake_instance.copy()


    @abimethod
    def claim_reward(
        self,
        interaction_fee: gtxn.PaymentTransaction,
        fee_payment: gtxn.PaymentTransaction,
        nfd_app_id: Application,
    ) -> tuple[UInt64, UInt64]:
        '''Claim The Current Reward Earned for this Staking Pool'''
        assert interaction_fee.amount == 330_000
        assert interaction_fee.receiver == Global.current_application_address
        
        total_transfers = UInt64(0)
        
        itxn.Payment(
            receiver=self.FEE_ADDRESS,
            amount=330_000,
            fee=Global.min_txn_fee
        ).submit()
        
        total_transfers += 1

        user_address = Address(Txn.sender)

        self._verify_gainify_nfd_ownership_pool(nfd_app_id)

        user_stake_instance = self.USER_STAKE_BOX[user_address].copy()

        original_stake_amount = user_stake_instance.stake_amount
        original_boost_amount = user_stake_instance.boost_amount

        new_user_stake_instance = self.calculate_earnings(user_stake_instance)

        diff = new_user_stake_instance.stake_amount.native - original_stake_amount.native
        boost_diff = new_user_stake_instance.boost_amount.native - original_boost_amount.native

        pool_end_time = self.POOL_START_TIME + self.POOL_LENGTH

        if Global.latest_timestamp < pool_end_time:
            self.add_stake_activity(stake_change=arc4UInt64(diff + boost_diff), increment=True)

        self.USER_STAKE_BOX[user_address] = new_user_stake_instance.copy()        
        reward_amount = new_user_stake_instance.reward_asset.native
        
        if reward_amount != 0:

            if self.REWARD_ASSET == 0:
                itxn.Payment(
                    amount=reward_amount,
                    fee=Global.min_txn_fee,
                    receiver=Txn.sender,
                ).submit()
                
            else:
                itxn.AssetTransfer(
                    xfer_asset=self.REWARD_ASSET,
                    asset_receiver=Txn.sender,
                    asset_amount=reward_amount,
                    fee=Global.min_txn_fee
                ).submit()
                
            new_user_stake_instance.reward_asset = arc4UInt64(0)
            total_transfers += 1
        
        assert fee_payment.amount >= Global.min_txn_fee * (total_transfers + 1)
        assert fee_payment.receiver == Global.current_application_address
        
        supplemental_reward_amount = UInt64(0)
        
        if self.SUPPLEMENTAL_REWARD_ASSET_AMOUNT != 0:

            supplemental_reward_amount = new_user_stake_instance.reward_supplement.native

            if supplemental_reward_amount > 0:

                if self.SUPPLEMENTAL_REWARD_ASSET == 0:
                    itxn.Payment(
                        receiver=Txn.sender,
                        amount=supplemental_reward_amount,
                        fee=Global.min_txn_fee
                    ).submit()
                else:
                    itxn.AssetTransfer(
                        xfer_asset=self.SUPPLEMENTAL_REWARD_ASSET,
                        asset_receiver=Txn.sender,
                        asset_amount=supplemental_reward_amount,
                        fee=Global.min_txn_fee
                    ).submit()
                
                new_user_stake_instance.reward_supplement = arc4UInt64(0)

                total_transfers += 1

        self.USER_STAKE_BOX[user_address] = new_user_stake_instance.copy()

        if self.SUPPLEMENTAL_REWARD_ASSET_AMOUNT != 0 and supplemental_reward_amount > 0:
            return reward_amount, supplemental_reward_amount
        
        return reward_amount, UInt64(0)
    
    
    
    @abimethod
    def claim_reward_and_unstake(
        self,
        interaction_fee: gtxn.PaymentTransaction,
        fee_payment: gtxn.PaymentTransaction,
        nfd_app_id: Application,
        unstake_amount: UInt64,
        unstake_all: UInt64
    ) -> None:
        '''Claim The Reward for this Staking Pool and Simulatenously Unstake Either a Partial Stake or Full Stake'''
        assert interaction_fee.amount == 330_000
        assert interaction_fee.receiver == Global.current_application_address
        
        total_transfers = UInt64(0)

        itxn.Payment(
            receiver=self.FEE_ADDRESS,
            amount=330_000,
            fee=Global.min_txn_fee
        ).submit()
        
        total_transfers += 1

        user_address = Address(Txn.sender)

        self._verify_gainify_nfd_ownership_pool(nfd_app_id)

        total_transfers += 1

        user_stake_instance = self.USER_STAKE_BOX[user_address].copy()

        original_amount = user_stake_instance.stake_amount.native
        original_boost_amount = user_stake_instance.boost_amount.native

        new_user_stake_instance = self.calculate_earnings(user_stake_instance)

        self.USER_STAKE_BOX[user_address] = new_user_stake_instance.copy()
        
        assert unstake_amount <= new_user_stake_instance.stake_amount.native

        new_amount = new_user_stake_instance.stake_amount.native
        new_boost_amount = new_user_stake_instance.boost_amount.native

        pool_end_time = self.POOL_START_TIME + self.POOL_LENGTH
        pool_ended = False

        if Global.latest_timestamp >= pool_end_time:
            pool_ended = True

        if unstake_all == 1 and not pool_ended:
            self.add_stake_activity(arc4UInt64(original_amount + original_boost_amount), False)

        else:
            add_diff = original_amount - new_amount

            if not pool_ended:

                if original_boost_amount > new_boost_amount:
                    boost_diff = original_boost_amount - new_boost_amount
                    self.add_stake_activity(arc4UInt64(add_diff + boost_diff), False)

                else:
                    boost_diff = new_boost_amount - original_boost_amount
                    self.add_stake_activity(arc4UInt64(add_diff - boost_diff), False)
                
            adjusted_user_stake_instance = self.USER_STAKE_BOX[user_address].copy()
            adjusted_user_stake_instance.stake_amount = arc4UInt64(user_stake_instance.stake_amount.native - unstake_amount) 
            adjusted_user_stake_instance.stake_time = arc4UInt64(Global.latest_timestamp)
            adjusted_boost_amounts = adjusted_user_stake_instance.stake_amount.native * 20
            adjusted_user_stake_instance.boost_amount = arc4UInt64(adjusted_boost_amounts // 100)
            adjusted_user_stake_instance.reward_asset = arc4UInt64(0)
            adjusted_user_stake_instance.reward_supplement = arc4UInt64(0)
            adjusted_user_stake_instance.last_counter = self.STAKE_ACTIVITY_COUNTER

            self.USER_STAKE_BOX[user_address] = adjusted_user_stake_instance.copy()

        reward_amount = new_user_stake_instance.reward_asset.native
        supplemental_reward_amount = new_user_stake_instance.reward_supplement.native
        
        if unstake_amount != 0:

            if unstake_all == 1:
                itxn.AssetTransfer(
                    xfer_asset=self.STAKE_ASSET,
                    asset_receiver=Txn.sender,
                    asset_amount=self.USER_STAKE_BOX[user_address].stake_amount.native,
                    fee=Global.min_txn_fee
                ).submit()
            else:
                itxn.AssetTransfer(
                    xfer_asset=self.STAKE_ASSET,
                    asset_receiver=Txn.sender,
                    asset_amount=unstake_amount,
                    fee=Global.min_txn_fee
                ).submit()
            
            total_transfers += 1

        if reward_amount != 0:

            if self.REWARD_ASSET != 0:
                itxn.AssetTransfer(
                    xfer_asset=self.REWARD_ASSET,
                    asset_receiver=Txn.sender,
                    asset_amount=reward_amount,
                    fee=Global.min_txn_fee
                ).submit()
                
            else:
                itxn.Payment(
                    receiver=Txn.sender,
                    amount=reward_amount,
                    fee=Global.min_txn_fee
                ).submit()

            new_user_stake_instance.reward_asset = arc4UInt64(0)
            total_transfers += 1
        
        if supplemental_reward_amount != 0:  

            if self.SUPPLEMENTAL_REWARD_ASSET != 0:     
                itxn.AssetTransfer(
                    xfer_asset=self.SUPPLEMENTAL_REWARD_ASSET,
                    asset_receiver=Txn.sender,
                    asset_amount=supplemental_reward_amount,
                    fee=Global.min_txn_fee
                ).submit()
                
            else:
                itxn.Payment(
                    receiver=Txn.sender,
                    amount=supplemental_reward_amount,
                    fee=Global.min_txn_fee
                ).submit()            
            
            new_user_stake_instance.reward_supplement = arc4UInt64(0)

            total_transfers += 1
        
        assert fee_payment.amount >= (Global.min_txn_fee * total_transfers)
        assert fee_payment.receiver == Global.current_application_address
        
        if unstake_all == 1:
            del self.USER_STAKE_BOX[user_address]
        
    
    
    @abimethod(allow_actions=['UpdateApplication'])
    def update(
        self
    ) -> None:
        '''Update the application using the creator address'''
        assert Txn.sender == Global.creator_address

    
    # @abimethod
    # def restructure_boxes(
    #     self,
    #     mbr_payment: gtxn.PaymentTransaction
    # ) -> None:
        '''
        This method was used to rectify a bug where box values exceeded 4096 bytes in length and could not
        be read regardless of the amount of box references used. This was an AVM limitation we did not have
        the foresight to anticipate with box maps. Admittedly, a benchmark where we overloaded boxes would 
        have been ideal here. However the project did not belong to us and we were paid *once* to create it, 
        and provided maintenance for free at no cost for some time. The issue did not arise until months after 
        we were already paid (which was not a substantial amount for 3 developers for several months) —
        the owners of the platform disappeared and left us with keys to core wallets for managing the contracts. 
        Although this method updated, and fixed that issue, a local state value assertion was accidentally added that 
        froze all staking pool contracts.
        '''
    #     initial_mbr_balance = Global.current_application_address.min_balance
    #     key = self.STAKE_ACTIVITY_COUNTER.bytes

    #     box_len, exists = op.Box.length(key)
    #     initial_box = BoxRef(key=key)

    #     if box_len >= 1010:
    #         item_count_bytes = arc4.UInt16(1008 // 16).bytes
    #         initial_box.replace(0, item_count_bytes)

    #         for i in urange(1010, box_len, 1008):
    #             chunk_length = UInt64(0)
    #             if box_len <= i + 1008:
    #                 chunk_length = box_len - i
    #             else:
    #                 chunk_length = UInt64(1008)

    #             current_box = BoxRef(key=key)
    #             extracted_content = current_box.extract(i, chunk_length)

    #             item_count = extracted_content.length // 16
    #             item_count_bytes = arc4.UInt16(item_count).bytes
    #             final_bytes = item_count_bytes + extracted_content

    #             self.STAKE_ACTIVITY_COUNTER = arc4.UInt64(self.STAKE_ACTIVITY_COUNTER.native + 1)
    #             next_key = self.STAKE_ACTIVITY_COUNTER
    #             box_ref = BoxRef(key=next_key.bytes)
    #             box_ref.put(final_bytes)

    #     initial_box.resize(1010)

    #     ending_mbr_balance = Global.current_application_address.min_balance

    #     diff = ending_mbr_balance - initial_mbr_balance
    #     amount_sent = mbr_payment.amount
    #     itxn.Payment(
    #         amount=amount_sent - diff,
    #         receiver=Txn.sender,
    #     ).submit()
    
