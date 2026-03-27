# Refine: Campus Innovation Fund DAO V2 更新升级计划

## 1. 最终判断

这份新设计应当融入当前旧工程，而且推荐采用 `基建增强型` 融合，而不是推翻旧工程重做。

原因很明确：

- 旧工程已经把 `Governor / Timelock / Treasury / Oracle / Aave / Evidence` 这条执行与安全主线做得很完整。
- 新设计补上的恰好是旧工程最薄弱的部分，也就是 `Proposal / Milestone / Reputation / Project Lifecycle` 这条业务治理主线。
- 两者合并后，不是简单功能叠加，而是把“安全执行层”和“业务语义层”真正对齐。

这份文档不再只是设计理念说明，而是面向后续 agent 执行实现的 `决策已锁定` 升级计划。

## 2. 锁定范围与非目标

### 2.1 本次升级的锁定目标

V2 必须实现的目标如下：

- 保留现有 `ERC20Votes -> InnovationGovernor -> TimelockController -> InnovationTreasury` 执行链。
- 引入 `Member`、`Proposal`、`Project`、`Milestone`、`Reputation` 五类一等业务对象。
- 让 proposal 不再只是 Governor calldata，而是完整业务提案。
- 让 milestone 不再只是数字顺序，而是可申报、可验证、可释放的显式结构。
- 引入 `token + reputation` 的混合投票权公式。
- 保留现有 treasury risk policy、Aave idle-fund management、NAV reporting。
- 保留现有 Sepolia demo/evidence/reporting 体系，但升级为能表达新业务流程。

### 2.2 明确不做的内容

以下内容继续保持 out of scope，不参与本轮升级：

- `delegated voting`
- `quadratic voting`
- `reviewer committee` 扩展版
- `slashing for dishonest milestone claims`
- `AI-generated proposal risk summary`
- `analytics comparing token-only vs hybrid voting outcomes`

说明：

- 这里的 “不做 delegated voting” 指不额外设计新型委托模型。
- 现有 `ERC20Votes` 自带的 token delegation 仍然保留，不需要删除。
- 这里的 “不做 reviewer committee 扩展版” 指不实现独立的委员会治理分支；milestone 验证仍通过 DAO 治理提案完成。

## 3. 核心设计原则

### 3.1 保留不变的系统主干

以下模块在 V2 中继续保留为核心，不做角色降级：

- `CampusInnovationFundToken`
- `InnovationGovernor`
- `TimelockController`
- `InnovationTreasury`
- `TreasuryOracle`
- `AaveWethAdapter`

### 3.2 新增但不替代主干的业务层

V2 新增的业务层不替代 Governor/Treasury，而是骑在它们之上：

- `ReputationRegistry`
- `HybridVotesAdapter`
- `FundingRegistry`

定位如下：

- `InnovationGovernor` 负责合法投票与合法执行。
- `FundingRegistry` 负责业务对象状态。
- `InnovationTreasury` 负责资金约束与资金释放。
- `HybridVotesAdapter` 负责把 token vote 和 reputation vote 合成为 Governor 可读取的投票权。
- `ReputationRegistry` 负责 reputation 的快照与更新。

### 3.3 关键设计决策

以下决策在本计划中视为已锁定，不再留给实现 agent 自行判断：

1. 混合治理采用 `token + reputation` 线性加权，不采用 quadratic。
2. Governor 仍使用 OpenZeppelin Governor 体系，不重写为完全自定义投票系统。
3. 混合投票通过 `HybridVotesAdapter` 实现，而不是把 reputation 直接塞进 token 合约。
4. Treasury 继续保持偏瘦；大部分业务状态放在 `FundingRegistry`，不把完整 workflow 塞进 `InnovationTreasury`。
5. milestone 验证由 DAO 治理提案完成，不引入独立 reviewer committee。
6. proposal/project 的富文本与证据详情以 `metadataURI` / `evidenceURI` 挂载在业务层，不塞进 treasury。

## 4. 公式与参数规范

这一节是本次 Refine 补全的重点。实现 agent 应直接以本节为公式来源。

### 4.1 记号定义

在 proposal snapshot 时刻 `s`：

- `T_u(s)` = 用户 `u` 的 token 投票权快照
- `T_total(s)` = token 总投票权快照
- `R_u(s)` = 用户 `u` 的 reputation 快照
- `R_total(s)` = 所有 active member 的 reputation 总快照
- `BASE(s)` = `T_total(s)`

默认权重常量：

- `TOKEN_WEIGHT_BPS = 6000`
- `REPUTATION_WEIGHT_BPS = 4000`
- `WEIGHT_DENOMINATOR = 10000`

### 4.2 混合投票权公式

混合投票权采用如下固定公式：

```text
TokenComponent_u(s)
  = floor(T_u(s) * TOKEN_WEIGHT_BPS / WEIGHT_DENOMINATOR)

ReputationComponent_u(s)
  = if R_total(s) == 0 then 0
    else floor(R_u(s) * REPUTATION_WEIGHT_BPS * BASE(s) / (R_total(s) * WEIGHT_DENOMINATOR))

HybridVotes_u(s)
  = TokenComponent_u(s) + ReputationComponent_u(s)
```

设计目的：

- `TokenComponent` 保留线性 token governance。
- `ReputationComponent` 不使用任意比例换算，而是按 reputation share 分摊固定的 40% 投票池。
- `HybridVotes` 的总量与 `BASE(s)` 同量纲，便于继续复用当前 Governor 的 quorum/threshold 逻辑。

### 4.3 混合总投票供给

```text
HybridTotalSupply(s) = BASE(s) = T_total(s)
```

这意味着：

- `GovernorVotesQuorumFraction` 仍可继续工作。
- `proposalThreshold`、`quorum` 仍以 CIF 总投票权单位衡量。
- 不需要重写 Governor 的 supply 语义。

### 4.4 Reputation 初值与更新公式

基础参数固定如下：

- `INITIAL_MEMBER_REPUTATION = 100`
- `MIN_REPUTATION = 0`
- `MAX_REPUTATION = 1000`

reputation 更新采用：

```text
ReputationNew = clamp(ReputationOld + Delta, MIN_REPUTATION, MAX_REPUTATION)
```

固定 delta 规则如下：

- 每次对正式治理 proposal 成功投票结算：`+2`
- 每个 milestone 成功释放：proposal proposer `+4`
- proposal 全部 milestones 完成后：proposal proposer 额外 `+10`
- milestone claim 被治理否决：proposal proposer `-8`

本轮不实现以下 reputation delta：

- reviewer accuracy reward
- slashing
- inactivity penalty

### 4.5 Treasury 相关公式

现有 treasury 约束继续保留，公式锁定如下：

单项目预算上限：

```text
MaxGrantAllowed = floor(totalManagedWeth * maxSingleGrantBps / 10000)
```

idle funds 存入 Aave 前的流动性底线：

```text
RequiredLiquidReserve = ceil(totalManagedWeth * minLiquidReserveBps / 10000)
```

milestone 金额约束：

```text
sum(milestone.amount[i]) == requestedFunding
```

project 释放上限：

```text
releasedTotal + nextMilestoneAmount <= approvedBudget
```

本轮明确规定：

- reserve floor 约束继续只用于 `depositIdleFunds`。
- 已批准的 milestone 支付不再额外受 reserve floor 阻拦。
- 若 liquid WETH 不足，则治理 proposal 应先执行 `withdrawIdleFunds`，再执行 `releaseMilestone`。

## 5. 目标架构

### 5.1 保留模块

V2 继续保留以下现有模块：

- `CampusInnovationFundToken`
- `InnovationGovernor`
- `InnovationTreasury`
- `TreasuryOracle`
- `AaveWethAdapter`

### 5.2 新增模块

V2 新增以下三个核心模块：

#### `ReputationRegistry`

职责：

- 存储 member reputation
- 维护 reputation checkpoints
- 维护 total active reputation checkpoints
- 提供 past reputation 查询
- 执行 governance 驱动的 reputation delta

#### `HybridVotesAdapter`

职责：

- 实现 `IVotes`
- 读取 `CampusInnovationFundToken` 的 past votes 与 total supply
- 读取 `ReputationRegistry` 的 past reputation 与 total reputation
- 返回 `HybridVotes_u(s)` 和 `HybridTotalSupply(s)`

#### `FundingRegistry`

职责：

- 存储 members、proposals、projects、milestones 的业务状态
- 管理 proposal 生命周期
- 管理 milestone claim 生命周期
- 记录 metadataURI 与 evidenceURI
- 记录 Governor proposal 与业务 proposal 的关联关系

### 5.3 分层结构

V2 最终结构固定为四层：

1. `Governance Spine`
   - `CampusInnovationFundToken`
   - `HybridVotesAdapter`
   - `InnovationGovernor`
   - `TimelockController`

2. `Funding Workflow`
   - `FundingRegistry`
   - `ReputationRegistry`

3. `Treasury & Risk`
   - `InnovationTreasury`
   - `TreasuryOracle`
   - `AaveWethAdapter`

4. `Presentation & Evidence`
   - frontend runtime bundle
   - deployments manifests
   - evidence/report scripts

## 6. 数据模型与状态机

这一节用于锁定实现 agent 需要遵循的业务对象结构。

### 6.1 Member

```solidity
struct Member {
    bool isRegistered;
    bool isActive;
    uint256 currentReputation;
}
```

规则：

- `isRegistered = true` 才允许提交 proposal。
- `isActive = true` 才计入 `R_total(s)`。
- `currentReputation` 由 `ReputationRegistry` 维护，不写入 token 合约。

### 6.2 Proposal

```solidity
enum ProposalStatus {
    Submitted,
    Voting,
    Approved,
    Rejected,
    Cancelled
}

struct Proposal {
    uint256 proposalId;
    address proposer;
    string title;
    string metadataURI;
    uint256 requestedFundingWeth;
    uint8 milestoneCount;
    ProposalStatus status;
    uint256 governorProposalId;
    bytes32 projectId;
}
```

说明：

- `proposalId` 是 `FundingRegistry` 内部业务 proposal id，不等于 `governorProposalId`。
- `metadataURI` 指向完整 proposal 内容，包括 description、deliverables、milestones 的富文本与附件。
- `projectId` 在 proposal 批准前为空，批准后写入。

### 6.3 Milestone

```solidity
enum MilestoneState {
    Locked,
    OpenForClaim,
    ClaimSubmitted,
    ClaimRejected,
    Released
}

struct Milestone {
    uint8 index;
    string description;
    uint256 amountWeth;
    string evidenceURI;
    MilestoneState state;
}
```

规则：

- proposal 提交时 milestones 创建，初始状态全部为 `Locked`。
- proposal 批准后：
  - `index = 0` 的 milestone 变为 `OpenForClaim`
  - 其余 milestones 继续 `Locked`
- 当前 milestone 成功 `Released` 后，下一个 milestone 自动变为 `OpenForClaim`

### 6.4 Project

```solidity
enum ProjectStatus {
    Active,
    Completed,
    Cancelled
}

struct Project {
    bytes32 projectId;
    uint256 sourceProposalId;
    address recipient;
    uint256 approvedBudgetWeth;
    uint256 releasedWeth;
    uint8 nextClaimableMilestone;
    ProjectStatus status;
}
```

说明：

- `Project` 是 proposal 被治理批准后的执行实体。
- Treasury 内部仍可保留现有瘦版 `Project` 记录。
- `FundingRegistry.Project` 是业务主视图；`InnovationTreasury.Project` 是资金执行视图。

### 6.5 状态流转

#### Proposal 状态流转

```text
Submitted -> Voting -> Approved
Submitted -> Voting -> Rejected
Submitted -> Voting -> Cancelled
Approved  -> Cancelled
```

触发规则：

- `Submitted -> Voting`: proposer 创建并成功提交对应 Governor proposal
- `Voting -> Approved`: Governor proposal 执行成功
- `Voting -> Rejected`: Governor proposal defeated/expired
- `Voting -> Cancelled`: proposer 或治理取消
- `Approved -> Cancelled`: 仅在异常治理决策中触发

#### Milestone 状态流转

```text
Locked -> OpenForClaim
OpenForClaim -> ClaimSubmitted
ClaimSubmitted -> ClaimRejected
ClaimSubmitted -> Released
```

触发规则：

- `Locked -> OpenForClaim`: proposal 批准或上一 milestone released
- `OpenForClaim -> ClaimSubmitted`: proposer 提交 evidenceURI
- `ClaimSubmitted -> ClaimRejected`: milestone approval governor proposal 被否决
- `ClaimSubmitted -> Released`: milestone approval governor proposal 执行成功，且 treasury release 成功

## 7. 合约与接口级升级计划

本节是给实现 agent 的最核心执行清单。

### 7.1 `ReputationRegistry`

建议新增合约：`src/governance/ReputationRegistry.sol`

必须实现的接口：

```solidity
interface IReputationRegistry {
    function registerMember(address member, uint256 initialReputation) external;
    function setMemberActive(address member, bool active) external;
    function applyReputationDelta(address member, int256 delta) external;
    function reputationOf(address member) external view returns (uint256);
    function isActiveMember(address member) external view returns (bool);
    function getPastReputation(address member, uint256 timepoint) external view returns (uint256);
    function getPastTotalReputation(uint256 timepoint) external view returns (uint256);
}
```

访问控制：

- `registerMember` / `setMemberActive` / `applyReputationDelta` 只能由 timelock 执行。
- 合约 owner 必须是 `TimelockController`。

实现要求：

- 使用 checkpoint 记录 member reputation 历史。
- 使用单独 checkpoint 记录 total active reputation 历史。
- 当 member inactive 时，从 active reputation total 中移除其当前 reputation。
- 当 member re-activate 时，再加入其当前 reputation。

### 7.2 `HybridVotesAdapter`

建议新增合约：`src/governance/HybridVotesAdapter.sol`

必须实现：

- `IVotes`
- `getPastVotes(account, timepoint)`
- `getPastTotalSupply(timepoint)`
- `getVotes(account)` 作为当前时刻版本

数据依赖：

- `CampusInnovationFundToken`
- `ReputationRegistry`

公式必须严格采用第 4 节，不允许实现 agent 自行替换。

实现要求：

- `getPastTotalSupply(timepoint)` 返回 `CampusInnovationFundToken.getPastTotalSupply(timepoint)`
- `getPastVotes(account, timepoint)` 返回 `HybridVotes_u(timepoint)`
- `clock()` 与 timepoint 语义跟随 `Governor` 使用的 block number 模式

部署要求：

- `InnovationGovernor` 的投票源从当前 token 切换为 `HybridVotesAdapter`
- `CampusInnovationFundToken` 本身不需要改名或改标准

### 7.3 `FundingRegistry`

建议新增合约：`src/funding/FundingRegistry.sol`

必须实现的接口方向：

```solidity
interface IFundingRegistry {
    function submitProposal(
        string calldata title,
        string calldata metadataURI,
        uint256 requestedFundingWeth,
        string[] calldata milestoneDescriptions,
        uint256[] calldata milestoneAmountsWeth
    ) external returns (uint256 proposalId);

    function linkGovernorProposal(uint256 proposalId, uint256 governorProposalId) external;

    function markProposalApproved(uint256 proposalId, bytes32 projectId) external;
    function markProposalRejected(uint256 proposalId) external;
    function cancelProposal(uint256 proposalId) external;

    function submitMilestoneClaim(
        uint256 proposalId,
        uint8 milestoneIndex,
        string calldata evidenceURI
    ) external;

    function markMilestoneRejected(uint256 proposalId, uint8 milestoneIndex) external;
    function markMilestoneReleased(uint256 proposalId, uint8 milestoneIndex) external;

    function getProposal(uint256 proposalId) external view returns (Proposal memory);
    function getProject(bytes32 projectId) external view returns (Project memory);
    function getMilestone(uint256 proposalId, uint8 milestoneIndex) external view returns (Milestone memory);
}
```

输入校验必须锁定为：

- `requestedFundingWeth > 0`
- `milestoneDescriptions.length == milestoneAmountsWeth.length`
- `1 <= milestoneCount <= 5`
- 每个 milestone amount `> 0`
- `sum(milestoneAmountsWeth) == requestedFundingWeth`
- 只有 active member 可以 submit proposal
- 只有 proposal proposer 可以 submit milestone claim
- milestone claim 必须按顺序提交

访问控制：

- `submitProposal` 与 `submitMilestoneClaim` 由普通 active member/proposer 调用
- `markProposalApproved` / `markProposalRejected` / `cancelProposal` / `markMilestoneRejected` / `markMilestoneReleased` 只能由 timelock 执行

### 7.4 `InnovationTreasury`

本轮不推翻 `InnovationTreasury`，只做最小必要改造。

保留：

- `approveProject`
- `releaseMilestone`
- `depositIdleFunds`
- `withdrawIdleFunds`
- `setRiskPolicy`
- `navUsd`

需要补充的约束与配套：

- `approveProject` 的 `maxBudgetWeth` 必须等于 `FundingRegistry.Proposal.requestedFundingWeth`
- `releaseMilestone` 的 `amountWeth` 必须等于对应 milestone 的固定 amount
- `projectId` 必须由 `FundingRegistry` 与 `InnovationTreasury` 共用同一生成规则

`projectId` 生成规则锁定为：

```text
projectId = keccak256(abi.encodePacked("PROJECT", proposalId, proposer, recipient))
```

### 7.5 `InnovationGovernor`

本轮不重写 Governor 模块栈，只做最小变化：

- token/vote source 改为 `HybridVotesAdapter`
- proposal、queue、execute 流程保持 OpenZeppelin 原逻辑
- quorum/threshold 常量保持当前量纲

实现 agent 不应在 V2 里另写一套自定义 Governor 状态机。

## 8. 治理提案批处理规范

为保证其他 agent 在执行时不需要自行发明 batch 方案，本节锁定治理 proposal 的 batched actions。

### 8.1 Proposal Approval 提案

当业务 proposal 进入治理表决时，对应的 Governor proposal 执行批次固定为：

1. `FundingRegistry.markProposalApproved(proposalId, projectId)`
2. `InnovationTreasury.approveProject(projectId, recipient, requestedFundingWeth, milestoneCount)`

若 proposal 被否决：

1. `FundingRegistry.markProposalRejected(proposalId)`

### 8.2 Milestone Release 提案

当某个 milestone claim 已提交且需要治理批准时，执行批次固定为：

1. 如果 liquid WETH 不足：`InnovationTreasury.withdrawIdleFunds(milestoneAmountWeth)`
2. `InnovationTreasury.releaseMilestone(projectId, milestoneIndex, milestoneAmountWeth)`
3. `FundingRegistry.markMilestoneReleased(proposalId, milestoneIndex)`
4. `ReputationRegistry.applyReputationDelta(proposer, +4)`

若该 milestone 是最后一个：

5. `ReputationRegistry.applyReputationDelta(proposer, +10)`

若 milestone claim 被否决：

1. `FundingRegistry.markMilestoneRejected(proposalId, milestoneIndex)`
2. `ReputationRegistry.applyReputationDelta(proposer, -8)`

### 8.3 Vote Participation Reputation 提案后结算

vote participation reward 的实现锁定为：

- 不在 `castVote` 时立即更新 reputation
- 在 proposal finalization 后由脚本或治理结算逻辑统一补发

原因：

- 避免在 Governor 投票流程中引入额外 side effect
- 保持 Governor 合约尽量接近现有结构

实现建议：

- 在 demo scripts / finalization script 中读取 `hasVoted`
- 对每个成功参与的地址调用 `ReputationRegistry.applyReputationDelta(voter, +2)`

## 9. 前端与运行时数据升级计划

V2 前端不能继续只展示固定三条治理 proposal。

### 9.1 新前端能力

前端必须新增以下页面或等价路由能力：

- `Submit Proposal`
- `Proposal Detail`
- `Project Detail`
- `Milestone Claim`
- `Treasury & NAV`
- `Evidence`

原有 `Overview / Proposals / Treasury / Evidence` 不需要删除，但 `Proposals` 页必须从固定 scenario 列表升级为业务 proposal 列表。

### 9.2 前端数据类型

`frontend/src/types.ts` 应补充：

- `Member`
- `ProposalStatus`
- `ProjectStatus`
- `MilestoneState`
- `FundingProposal`
- `FundingProject`
- `FundingMilestone`

### 9.3 运行时 manifest

为避免破坏旧流程，runtime 数据采用 “保留旧 manifest + 增加新 manifest” 策略。

新增：

- `funding_state.sepolia.json`

内容至少包括：

- active members
- proposals
- projects
- milestones
- reputation snapshots

保留：

- `proposal_scenarios.sepolia.json`
- `demo_evidence.sepolia.json`
- `deployments.sepolia.json`

## 10. 部署与迁移顺序

执行 agent 必须按以下顺序部署与接线：

1. 部署 `CampusInnovationFundToken`
2. 部署 `ReputationRegistry`
3. 部署 `HybridVotesAdapter(token, reputationRegistry)`
4. 部署 `TimelockController`
5. 部署 `InnovationGovernor(votesSource = hybridVotesAdapter, timelock)`
6. 部署 `TreasuryOracle`
7. 部署 `AaveWethAdapter`
8. 部署 `InnovationTreasury(timelock, weth, oracle, aaveAdapter)`
9. 部署 `FundingRegistry(timelock, treasury, reputationRegistry)`
10. 为 demo 成员注册初始 reputation
11. 导出新的 runtime/config/evidence manifests

迁移要求：

- 不删除当前旧的三提案 demo
- 先让旧 demo 在新架构下仍能解释为简化路径
- 再逐步加上新 proposal / milestone claim / reputation 演示

## 11. 分阶段实施计划

这一节是面向 agent 执行的阶段化任务清单。

### Phase 1: 合约主干补齐

目标：

- 新增 `ReputationRegistry`
- 新增 `HybridVotesAdapter`
- 新增 `FundingRegistry`
- 修改部署脚本与接口 bundle

交付完成标准：

- Governor 能从 `HybridVotesAdapter` 读取 votes
- `FundingRegistry` 能提交 proposal 与 milestone claim
- `ReputationRegistry` 能记录与查询 past reputation

### Phase 2: 治理工作流接线

目标：

- 将 proposal approval 与 milestone release 变成标准 governance batch
- 让 `FundingRegistry` 与 `InnovationTreasury` 在 `projectId` 上一致
- 完成 reputation delta 的批次更新逻辑

交付完成标准：

- 业务 proposal 可通过治理批准并激活 project
- milestone claim 可通过治理批准并触发 tranche release
- proposer reputation 按固定公式更新

### Phase 3: 前端与 runtime 升级

目标：

- 页面从固定 scenario 升级为读取真实 funding state
- 增加 proposal/project/milestone 详情展示
- 增加 member reputation 展示

交付完成标准：

- 前端可以展示 proposal lifecycle
- 前端可以提交 proposal 与 milestone claim
- 前端可以展示 current hybrid voting context

### Phase 4: Demo 与证据链升级

目标：

- 升级 seed/demo/export scripts
- 让 evidence 能覆盖新工作流
- 让报告内容能解释混合治理与业务流程层

交付完成标准：

- 生成新的 `funding_state.sepolia.json`
- evidence 中出现 proposal submit / approval / claim / release / reputation updates
- 旧 demo 与新 demo 都能运行

## 12. 测试矩阵与验收标准

这一节也是实现 agent 的直接验收清单。

### 12.1 合约单元测试

必须新增的测试类别：

- `ReputationRegistry`
  - register member
  - activate/deactivate member
  - apply delta
  - checkpoint correctness

- `HybridVotesAdapter`
  - token-only case
  - reputation-only effective case
  - zero `R_total` case
  - `HybridTotalSupply == token total supply`
  - formula rounding consistency

- `FundingRegistry`
  - submit proposal
  - invalid milestone sum reverts
  - only proposer can submit milestone claim
  - milestone sequence enforcement
  - proposal state transitions
  - milestone state transitions

- `InnovationTreasury`
  - current tests retained
  - release amount must match milestone amount via workflow integration tests

### 12.2 集成测试

必须新增的集成场景：

1. `happy path`
   - active member submit proposal
   - governance vote passes
   - project approved
   - milestone 0 claim submitted
   - governance vote passes
   - treasury releases tranche
   - reputation increases

2. `proposal rejected`
   - proposal enters voting
   - proposal defeated
   - status becomes rejected
   - treasury untouched

3. `milestone rejected`
   - project approved
   - claim submitted
   - milestone approval proposal defeated
   - milestone state becomes rejected
   - reputation decreases
   - no treasury release

4. `withdraw then release`
   - insufficient liquid WETH
   - governance batch withdraws from Aave
   - same batch releases milestone

5. `hybrid voting divergence`
   - two accounts with different token/reputation compositions
   - verify `HybridVotesAdapter` returns expected vote weights by formula

### 12.3 前端验收

前端最少必须满足：

- 能显示 funding proposals 列表
- 能显示 project 当前 released / remaining 状态
- 能显示 milestone state 与 evidenceURI
- 能显示 member reputation
- 能显示 treasury liquid/supplied/NAV

### 12.4 最终验收标准

只有同时满足下面五条，V2 才算完成：

1. Governance 主干未被破坏
2. 混合投票公式已落地
3. proposal/project/milestone/reputation 都是链上或准链上一等对象
4. 现有 treasury risk + Aave + NAV 仍然正常
5. 前端与 evidence 能完整讲出新业务流程

## 13. 兼容性要求

V2 必须保留对当前仓库叙事的兼容性：

- 旧 demo 的三条 proposal 仍可保留
- 旧 `InnovationTreasury` 风险策略仍可保留
- 旧 `TreasuryOracle` 和 `AaveWethAdapter` 不应被弱化为可选项

在答辩或展示层面，V2 的标准叙事应变成：

`这是一个以 Governor/Timelock/Treasury 作为安全执行主干、以 Proposal/Milestone/Reputation 作为业务治理层的项目资金 DAO。`

## 14. 给后续实现 agent 的直接执行摘要

如果后续 agent 只看这一节，也应能开始干活。

执行顺序固定为：

1. 新增 `ReputationRegistry`
2. 新增 `HybridVotesAdapter`
3. 新增 `FundingRegistry`
4. 改部署脚本让 Governor 指向 `HybridVotesAdapter`
5. 写 proposal/project/milestone 状态机测试
6. 写 governance batch 集成测试
7. 改前端类型与 runtime manifest
8. 改 demo/evidence scripts

实现中不得自行改动的关键决策：

- 混合投票公式必须用 `60% token + 40% reputation`
- 不做 quadratic
- 不做独立 reviewer committee
- milestone 验证通过 DAO proposal 完成
- `InnovationTreasury` 不负责保存完整业务富状态
- `FundingRegistry` 承担 workflow source of truth

这份 Refine 的最终主张是：

`V2 不推翻旧工程，而是在旧工程成熟的治理与资金基础设施上，增加完整的 proposal / milestone / reputation 业务治理层，并用固定的混合投票公式把两者接成一个可实现、可测试、可展示的高级 DAO 系统。`
