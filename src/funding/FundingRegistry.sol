// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {IGovernor} from "@openzeppelin/contracts/governance/IGovernor.sol";

import {IFundingRegistry} from "../interfaces/IFundingRegistry.sol";
import {IInnovationGovernor} from "../interfaces/IInnovationGovernor.sol";
import {IReputationRegistry} from "../interfaces/IReputationRegistry.sol";

contract FundingRegistry is IFundingRegistry, Ownable {
    uint8 public constant MAX_MILESTONE_COUNT = 5;
    int256 public constant VOTE_PARTICIPATION_REPUTATION_DELTA = 2;
    int256 public constant MILESTONE_RELEASE_REPUTATION_DELTA = 4;
    int256 public constant PROJECT_COMPLETION_REPUTATION_DELTA = 10;
    int256 public constant MILESTONE_REJECTION_REPUTATION_DELTA = -8;

    error InvalidTimelock(address timelock);
    error InvalidGovernor(address governor);
    error InvalidReputationRegistry(address reputationRegistry);
    error OwnershipTransferDisabled();
    error ProposalNotFound(uint256 proposalId);
    error ProjectNotFound(bytes32 projectId);
    error InvalidProposalRecipient(address recipient);
    error InvalidRequestedFunding(uint256 requestedFundingWeth);
    error InvalidMilestoneConfiguration(uint256 descriptionCount, uint256 amountCount);
    error InvalidMilestoneCount(uint256 milestoneCount);
    error InvalidMilestoneAmount(uint8 milestoneIndex, uint256 amountWeth);
    error InvalidMilestoneIndex(uint256 proposalId, uint8 milestoneIndex);
    error InactiveMember(address member);
    error UnauthorizedProposer(address caller, uint256 proposalId);
    error InvalidProposalStatus(uint256 proposalId, ProposalStatus expectedStatus, ProposalStatus actualStatus);
    error GovernorProposalAlreadyLinked(uint256 proposalId);
    error InvalidGovernorProposalState(uint256 governorProposalId, IGovernor.ProposalState actualState);
    error InvalidGovernorProposalId(uint256 governorProposalId);
    error InvalidEvidenceURI();
    error InvalidMetadataURI();
    error InvalidTitle();
    error InvalidProjectId(bytes32 expectedProjectId, bytes32 actualProjectId);
    error ProjectAlreadyExists(bytes32 projectId);
    error MilestoneGovernorProposalAlreadyLinked(uint256 proposalId, uint8 milestoneIndex);
    error MilestoneNotClaimable(uint256 proposalId, uint8 milestoneIndex, MilestoneState actualState);
    error ProposalOutcomeNotFinalizable(uint256 proposalId, IGovernor.ProposalState actualState);
    error MilestoneOutcomeNotFinalizable(
        uint256 proposalId,
        uint8 milestoneIndex,
        IGovernor.ProposalState actualState
    );
    error VoteParticipationAlreadySettled(uint256 proposalId, address voter);
    error VoteParticipationNotRecorded(uint256 proposalId, address voter);
    error EmptyVoterBatch();
    error InvalidProjectStatus(bytes32 projectId, ProjectStatus expectedStatus, ProjectStatus actualStatus);
    error DuplicateProjectApproval(uint256 proposalId);

    event ProposalSubmitted(
        uint256 indexed proposalId,
        address indexed proposer,
        address indexed recipient,
        uint256 requestedFundingWeth,
        uint8 milestoneCount
    );
    event ProposalGovernorLinked(uint256 indexed proposalId, uint256 indexed governorProposalId);
    event ProposalApproved(uint256 indexed proposalId, bytes32 indexed projectId);
    event ProposalRejected(uint256 indexed proposalId);
    event ProposalCancelled(uint256 indexed proposalId, bytes32 indexed projectId);
    event MilestoneClaimSubmitted(uint256 indexed proposalId, uint8 indexed milestoneIndex, string evidenceURI);
    event MilestoneGovernorLinked(uint256 indexed proposalId, uint8 indexed milestoneIndex, uint256 governorProposalId);
    event MilestoneRejected(uint256 indexed proposalId, uint8 indexed milestoneIndex);
    event MilestoneReleased(uint256 indexed proposalId, uint8 indexed milestoneIndex, bytes32 indexed projectId);
    event VoteParticipationSettled(uint256 indexed proposalId, address indexed voter);
    event MilestoneVoteParticipationSettled(uint256 indexed proposalId, uint8 indexed milestoneIndex, address indexed voter);

    IInnovationGovernor public immutable innovationGovernor;
    IReputationRegistry public immutable reputationRegistry;

    uint256 private _nextProposalId = 1;

    mapping(uint256 proposalId => Proposal) private _proposals;
    mapping(uint256 proposalId => Milestone[]) private _proposalMilestones;
    mapping(bytes32 projectId => Project) private _projects;
    mapping(uint256 proposalId => mapping(address voter => bool settled)) private _voteParticipationSettled;
    mapping(uint256 proposalId => mapping(uint8 milestoneIndex => mapping(address voter => bool settled)))
        private _milestoneVoteParticipationSettled;

    uint256[] private _proposalIds;
    bytes32[] private _projectIds;

    constructor(
        address timelock,
        address governor,
        address reputationRegistry_
    ) Ownable(timelock) {
        if (timelock == address(0)) {
            revert InvalidTimelock(address(0));
        }
        if (governor == address(0)) {
            revert InvalidGovernor(address(0));
        }
        if (reputationRegistry_ == address(0)) {
            revert InvalidReputationRegistry(address(0));
        }

        innovationGovernor = IInnovationGovernor(governor);
        reputationRegistry = IReputationRegistry(reputationRegistry_);
    }

    function transferOwnership(address) public pure override {
        revert OwnershipTransferDisabled();
    }

    function renounceOwnership() public pure override {
        revert OwnershipTransferDisabled();
    }

    function submitProposal(
        string calldata title,
        string calldata metadataURI,
        address recipient,
        uint256 requestedFundingWeth,
        string[] calldata milestoneDescriptions,
        uint256[] calldata milestoneAmountsWeth
    ) external override returns (uint256 proposalId) {
        if (!reputationRegistry.isActiveMember(msg.sender)) {
            revert InactiveMember(msg.sender);
        }
        if (bytes(title).length == 0) {
            revert InvalidTitle();
        }
        if (bytes(metadataURI).length == 0) {
            revert InvalidMetadataURI();
        }
        if (recipient == address(0)) {
            revert InvalidProposalRecipient(address(0));
        }
        if (requestedFundingWeth == 0) {
            revert InvalidRequestedFunding(requestedFundingWeth);
        }
        if (milestoneDescriptions.length != milestoneAmountsWeth.length) {
            revert InvalidMilestoneConfiguration(milestoneDescriptions.length, milestoneAmountsWeth.length);
        }
        if (milestoneDescriptions.length == 0 || milestoneDescriptions.length > MAX_MILESTONE_COUNT) {
            revert InvalidMilestoneCount(milestoneDescriptions.length);
        }

        uint256 amountSum = 0;
        proposalId = _nextProposalId++;

        Proposal storage proposal = _proposals[proposalId];
        proposal.proposalId = proposalId;
        proposal.proposer = msg.sender;
        proposal.recipient = recipient;
        proposal.title = title;
        proposal.metadataURI = metadataURI;
        proposal.requestedFundingWeth = requestedFundingWeth;
        proposal.milestoneCount = uint8(milestoneDescriptions.length);
        proposal.status = ProposalStatus.Submitted;

        for (uint8 index = 0; index < milestoneDescriptions.length; ++index) {
            uint256 milestoneAmount = milestoneAmountsWeth[index];
            if (milestoneAmount == 0) {
                revert InvalidMilestoneAmount(index, milestoneAmount);
            }

            amountSum += milestoneAmount;
            _proposalMilestones[proposalId].push(
                Milestone({
                    index: index,
                    description: milestoneDescriptions[index],
                    amountWeth: milestoneAmount,
                    evidenceURI: "",
                    state: MilestoneState.Locked,
                    claimGovernorProposalId: 0
                })
            );
        }

        if (amountSum != requestedFundingWeth) {
            revert InvalidRequestedFunding(requestedFundingWeth);
        }

        _proposalIds.push(proposalId);

        emit ProposalSubmitted(proposalId, msg.sender, recipient, requestedFundingWeth, proposal.milestoneCount);
    }

    function linkGovernorProposal(uint256 proposalId, uint256 governorProposalId) external override {
        Proposal storage proposal = _proposalState(proposalId);
        if (msg.sender != proposal.proposer) {
            revert UnauthorizedProposer(msg.sender, proposalId);
        }
        if (proposal.status != ProposalStatus.Submitted) {
            revert InvalidProposalStatus(proposalId, ProposalStatus.Submitted, proposal.status);
        }
        if (proposal.governorProposalId != 0) {
            revert GovernorProposalAlreadyLinked(proposalId);
        }

        IGovernor.ProposalState governorState = _readGovernorState(governorProposalId);
        if (
            governorState != IGovernor.ProposalState.Pending
                && governorState != IGovernor.ProposalState.Active
                && governorState != IGovernor.ProposalState.Succeeded
                && governorState != IGovernor.ProposalState.Queued
        ) {
            revert InvalidGovernorProposalState(governorProposalId, governorState);
        }

        proposal.governorProposalId = governorProposalId;
        proposal.status = ProposalStatus.Voting;

        emit ProposalGovernorLinked(proposalId, governorProposalId);
    }

    function linkMilestoneGovernorProposal(
        uint256 proposalId,
        uint8 milestoneIndex,
        uint256 governorProposalId
    ) external override {
        Proposal storage proposal = _proposalState(proposalId);
        if (msg.sender != proposal.proposer) {
            revert UnauthorizedProposer(msg.sender, proposalId);
        }
        if (proposal.status != ProposalStatus.Approved) {
            revert InvalidProposalStatus(proposalId, ProposalStatus.Approved, proposal.status);
        }

        Milestone storage milestone = _milestoneState(proposalId, milestoneIndex);
        if (milestone.state != MilestoneState.ClaimSubmitted) {
            revert MilestoneNotClaimable(proposalId, milestoneIndex, milestone.state);
        }
        if (milestone.claimGovernorProposalId != 0) {
            revert MilestoneGovernorProposalAlreadyLinked(proposalId, milestoneIndex);
        }

        IGovernor.ProposalState governorState = _readGovernorState(governorProposalId);
        if (
            governorState != IGovernor.ProposalState.Pending
                && governorState != IGovernor.ProposalState.Active
                && governorState != IGovernor.ProposalState.Succeeded
                && governorState != IGovernor.ProposalState.Queued
        ) {
            revert InvalidGovernorProposalState(governorProposalId, governorState);
        }

        milestone.claimGovernorProposalId = governorProposalId;

        emit MilestoneGovernorLinked(proposalId, milestoneIndex, governorProposalId);
    }

    function markProposalApproved(uint256 proposalId, bytes32 projectId) external override onlyOwner {
        Proposal storage proposal = _proposalState(proposalId);
        if (proposal.status != ProposalStatus.Voting) {
            revert InvalidProposalStatus(proposalId, ProposalStatus.Voting, proposal.status);
        }
        if (proposal.governorProposalId == 0) {
            revert InvalidGovernorProposalId(0);
        }
        if (_projects[projectId].projectId != bytes32(0)) {
            revert ProjectAlreadyExists(projectId);
        }

        IGovernor.ProposalState governorState = _readGovernorState(proposal.governorProposalId);
        if (governorState != IGovernor.ProposalState.Executed) {
            revert InvalidGovernorProposalState(proposal.governorProposalId, governorState);
        }

        bytes32 expectedProjectId = deriveProjectId(proposalId, proposal.proposer, proposal.recipient);
        if (projectId != expectedProjectId) {
            revert InvalidProjectId(expectedProjectId, projectId);
        }
        if (proposal.projectId != bytes32(0)) {
            revert DuplicateProjectApproval(proposalId);
        }

        proposal.status = ProposalStatus.Approved;
        proposal.projectId = projectId;

        _projects[projectId] = Project({
            projectId: projectId,
            sourceProposalId: proposalId,
            recipient: proposal.recipient,
            approvedBudgetWeth: proposal.requestedFundingWeth,
            releasedWeth: 0,
            nextClaimableMilestone: 0,
            status: ProjectStatus.Active
        });
        _projectIds.push(projectId);

        _proposalMilestones[proposalId][0].state = MilestoneState.OpenForClaim;

        emit ProposalApproved(proposalId, projectId);
    }

    function markProposalRejected(uint256 proposalId) external override onlyOwner {
        Proposal storage proposal = _proposalState(proposalId);
        if (proposal.status != ProposalStatus.Voting) {
            revert InvalidProposalStatus(proposalId, ProposalStatus.Voting, proposal.status);
        }
        if (proposal.governorProposalId == 0) {
            revert InvalidGovernorProposalId(0);
        }

        IGovernor.ProposalState governorState = _readGovernorState(proposal.governorProposalId);
        if (
            governorState != IGovernor.ProposalState.Defeated
                && governorState != IGovernor.ProposalState.Expired
        ) {
            revert InvalidGovernorProposalState(proposal.governorProposalId, governorState);
        }

        proposal.status = ProposalStatus.Rejected;

        emit ProposalRejected(proposalId);
    }

    function cancelProposal(uint256 proposalId) external override onlyOwner {
        Proposal storage proposal = _proposalState(proposalId);
        if (proposal.status == ProposalStatus.Rejected || proposal.status == ProposalStatus.Cancelled) {
            revert InvalidProposalStatus(proposalId, ProposalStatus.Voting, proposal.status);
        }

        proposal.status = ProposalStatus.Cancelled;

        if (proposal.projectId != bytes32(0)) {
            Project storage project = _projectState(proposal.projectId);
            if (project.status == ProjectStatus.Active) {
                project.status = ProjectStatus.Cancelled;
            }
        }

        emit ProposalCancelled(proposalId, proposal.projectId);
    }

    function submitMilestoneClaim(uint256 proposalId, uint8 milestoneIndex, string calldata evidenceURI) external override {
        Proposal storage proposal = _proposalState(proposalId);
        if (msg.sender != proposal.proposer) {
            revert UnauthorizedProposer(msg.sender, proposalId);
        }
        if (proposal.status != ProposalStatus.Approved) {
            revert InvalidProposalStatus(proposalId, ProposalStatus.Approved, proposal.status);
        }
        if (bytes(evidenceURI).length == 0) {
            revert InvalidEvidenceURI();
        }

        Project storage project = _projectState(proposal.projectId);
        if (project.status != ProjectStatus.Active) {
            revert InvalidProjectStatus(proposal.projectId, ProjectStatus.Active, project.status);
        }
        if (project.nextClaimableMilestone != milestoneIndex) {
            revert InvalidMilestoneIndex(proposalId, milestoneIndex);
        }

        Milestone storage milestone = _milestoneState(proposalId, milestoneIndex);
        if (milestone.state != MilestoneState.OpenForClaim) {
            revert MilestoneNotClaimable(proposalId, milestoneIndex, milestone.state);
        }

        milestone.evidenceURI = evidenceURI;
        milestone.state = MilestoneState.ClaimSubmitted;

        emit MilestoneClaimSubmitted(proposalId, milestoneIndex, evidenceURI);
    }

    function markMilestoneRejected(uint256 proposalId, uint8 milestoneIndex) external override onlyOwner {
        Proposal storage proposal = _proposalState(proposalId);
        if (proposal.status != ProposalStatus.Approved) {
            revert InvalidProposalStatus(proposalId, ProposalStatus.Approved, proposal.status);
        }

        Milestone storage milestone = _milestoneState(proposalId, milestoneIndex);
        if (milestone.state != MilestoneState.ClaimSubmitted) {
            revert MilestoneNotClaimable(proposalId, milestoneIndex, milestone.state);
        }
        if (milestone.claimGovernorProposalId != 0) {
            IGovernor.ProposalState governorState = _readGovernorState(milestone.claimGovernorProposalId);
            if (
                governorState != IGovernor.ProposalState.Defeated
                    && governorState != IGovernor.ProposalState.Expired
                    && governorState != IGovernor.ProposalState.Canceled
            ) {
                revert InvalidGovernorProposalState(milestone.claimGovernorProposalId, governorState);
            }
        }

        milestone.state = MilestoneState.ClaimRejected;

        emit MilestoneRejected(proposalId, milestoneIndex);
    }

    function markMilestoneReleased(uint256 proposalId, uint8 milestoneIndex) external override onlyOwner {
        Proposal storage proposal = _proposalState(proposalId);
        if (proposal.status != ProposalStatus.Approved) {
            revert InvalidProposalStatus(proposalId, ProposalStatus.Approved, proposal.status);
        }

        Project storage project = _projectState(proposal.projectId);
        if (project.status != ProjectStatus.Active) {
            revert InvalidProjectStatus(project.projectId, ProjectStatus.Active, project.status);
        }
        if (project.nextClaimableMilestone != milestoneIndex) {
            revert InvalidMilestoneIndex(proposalId, milestoneIndex);
        }

        Milestone storage milestone = _milestoneState(proposalId, milestoneIndex);
        if (milestone.state != MilestoneState.ClaimSubmitted) {
            revert MilestoneNotClaimable(proposalId, milestoneIndex, milestone.state);
        }
        if (milestone.claimGovernorProposalId == 0) {
            revert InvalidGovernorProposalId(0);
        }

        IGovernor.ProposalState governorState = _readGovernorState(milestone.claimGovernorProposalId);
        if (governorState != IGovernor.ProposalState.Executed) {
            revert InvalidGovernorProposalState(milestone.claimGovernorProposalId, governorState);
        }

        milestone.state = MilestoneState.Released;
        project.releasedWeth += milestone.amountWeth;
        project.nextClaimableMilestone += 1;
        reputationRegistry.applyWorkflowReputationDelta(proposal.proposer, MILESTONE_RELEASE_REPUTATION_DELTA);

        if (project.nextClaimableMilestone == proposal.milestoneCount) {
            project.status = ProjectStatus.Completed;
            reputationRegistry.applyWorkflowReputationDelta(proposal.proposer, PROJECT_COMPLETION_REPUTATION_DELTA);
        } else {
            _proposalMilestones[proposalId][project.nextClaimableMilestone].state = MilestoneState.OpenForClaim;
        }

        emit MilestoneReleased(proposalId, milestoneIndex, project.projectId);
    }

    function finalizeProposalOutcome(uint256 proposalId) external override {
        Proposal storage proposal = _proposalState(proposalId);
        if (proposal.status != ProposalStatus.Voting) {
            revert InvalidProposalStatus(proposalId, ProposalStatus.Voting, proposal.status);
        }
        if (proposal.governorProposalId == 0) {
            revert InvalidGovernorProposalId(0);
        }

        IGovernor.ProposalState governorState = _readGovernorState(proposal.governorProposalId);
        if (
            governorState == IGovernor.ProposalState.Defeated
                || governorState == IGovernor.ProposalState.Expired
        ) {
            proposal.status = ProposalStatus.Rejected;
            emit ProposalRejected(proposalId);
            return;
        }
        if (governorState == IGovernor.ProposalState.Canceled) {
            proposal.status = ProposalStatus.Cancelled;
            emit ProposalCancelled(proposalId, proposal.projectId);
            return;
        }

        revert ProposalOutcomeNotFinalizable(proposalId, governorState);
    }

    function finalizeMilestoneOutcome(uint256 proposalId, uint8 milestoneIndex) external override {
        Proposal storage proposal = _proposalState(proposalId);
        if (proposal.status != ProposalStatus.Approved) {
            revert InvalidProposalStatus(proposalId, ProposalStatus.Approved, proposal.status);
        }

        Milestone storage milestone = _milestoneState(proposalId, milestoneIndex);
        if (milestone.state != MilestoneState.ClaimSubmitted) {
            revert MilestoneNotClaimable(proposalId, milestoneIndex, milestone.state);
        }
        if (milestone.claimGovernorProposalId == 0) {
            revert InvalidGovernorProposalId(0);
        }

        IGovernor.ProposalState governorState = _readGovernorState(milestone.claimGovernorProposalId);
        if (
            governorState != IGovernor.ProposalState.Defeated
                && governorState != IGovernor.ProposalState.Expired
                && governorState != IGovernor.ProposalState.Canceled
        ) {
            revert MilestoneOutcomeNotFinalizable(proposalId, milestoneIndex, governorState);
        }

        milestone.state = MilestoneState.ClaimRejected;
        reputationRegistry.applyWorkflowReputationDelta(proposal.proposer, MILESTONE_REJECTION_REPUTATION_DELTA);

        emit MilestoneRejected(proposalId, milestoneIndex);
    }

    function settleVoteParticipationBatch(uint256 proposalId, address[] calldata voters) external override {
        Proposal storage proposal = _proposalState(proposalId);
        if (proposal.status == ProposalStatus.Submitted || proposal.status == ProposalStatus.Voting) {
            revert InvalidProposalStatus(proposalId, ProposalStatus.Approved, proposal.status);
        }
        if (proposal.governorProposalId == 0) {
            revert InvalidGovernorProposalId(0);
        }
        if (voters.length == 0) {
            revert EmptyVoterBatch();
        }

        for (uint256 index = 0; index < voters.length; ++index) {
            address voter = voters[index];
            if (_voteParticipationSettled[proposalId][voter]) {
                revert VoteParticipationAlreadySettled(proposalId, voter);
            }
            if (!innovationGovernor.hasVoted(proposal.governorProposalId, voter)) {
                revert VoteParticipationNotRecorded(proposalId, voter);
            }

            _voteParticipationSettled[proposalId][voter] = true;
            reputationRegistry.applyWorkflowReputationDelta(voter, VOTE_PARTICIPATION_REPUTATION_DELTA);

            emit VoteParticipationSettled(proposalId, voter);
        }
    }

    function settleMilestoneVoteParticipationBatch(
        uint256 proposalId,
        uint8 milestoneIndex,
        address[] calldata voters
    ) external override {
        Proposal storage proposal = _proposalState(proposalId);
        if (proposal.status != ProposalStatus.Approved) {
            revert InvalidProposalStatus(proposalId, ProposalStatus.Approved, proposal.status);
        }
        if (voters.length == 0) {
            revert EmptyVoterBatch();
        }

        Milestone storage milestone = _milestoneState(proposalId, milestoneIndex);
        if (milestone.state != MilestoneState.Released && milestone.state != MilestoneState.ClaimRejected) {
            revert MilestoneNotClaimable(proposalId, milestoneIndex, milestone.state);
        }
        if (milestone.claimGovernorProposalId == 0) {
            revert InvalidGovernorProposalId(0);
        }

        for (uint256 index = 0; index < voters.length; ++index) {
            address voter = voters[index];
            if (_milestoneVoteParticipationSettled[proposalId][milestoneIndex][voter]) {
                revert VoteParticipationAlreadySettled(proposalId, voter);
            }
            if (!innovationGovernor.hasVoted(milestone.claimGovernorProposalId, voter)) {
                revert VoteParticipationNotRecorded(proposalId, voter);
            }

            _milestoneVoteParticipationSettled[proposalId][milestoneIndex][voter] = true;
            reputationRegistry.applyWorkflowReputationDelta(voter, VOTE_PARTICIPATION_REPUTATION_DELTA);

            emit MilestoneVoteParticipationSettled(proposalId, milestoneIndex, voter);
        }
    }

    function deriveProjectId(uint256 proposalId, address proposer, address recipient) public pure override returns (bytes32) {
        return keccak256(abi.encodePacked("PROJECT", proposalId, proposer, recipient));
    }

    function getProposal(uint256 proposalId) external view override returns (Proposal memory) {
        return _proposalState(proposalId);
    }

    function getProposalByIndex(uint256 index) external view override returns (Proposal memory) {
        return _proposals[_proposalIds[index]];
    }

    function proposalCount() external view override returns (uint256) {
        return _proposalIds.length;
    }

    function getProject(bytes32 projectId) external view override returns (Project memory) {
        return _projects[projectId];
    }

    function getProjectByIndex(uint256 index) external view override returns (Project memory) {
        return _projects[_projectIds[index]];
    }

    function projectCount() external view override returns (uint256) {
        return _projectIds.length;
    }

    function getMilestone(uint256 proposalId, uint8 milestoneIndex) external view override returns (Milestone memory) {
        return _proposalMilestones[proposalId][milestoneIndex];
    }

    function milestoneCount(uint256 proposalId) external view override returns (uint256) {
        _ensureProposalExists(proposalId);
        return _proposalMilestones[proposalId].length;
    }

    function getMember(address member) external view override returns (Member memory) {
        return _memberView(member);
    }

    function getMemberByIndex(uint256 index) external view override returns (Member memory) {
        return _memberView(reputationRegistry.memberAtIndex(index));
    }

    function memberCount() external view override returns (uint256) {
        return reputationRegistry.memberCount();
    }

    function hasVoteParticipationSettled(uint256 proposalId, address voter) external view override returns (bool) {
        return _voteParticipationSettled[proposalId][voter];
    }

    function hasMilestoneVoteParticipationSettled(
        uint256 proposalId,
        uint8 milestoneIndex,
        address voter
    ) external view override returns (bool) {
        return _milestoneVoteParticipationSettled[proposalId][milestoneIndex][voter];
    }

    function _proposalState(uint256 proposalId) internal view returns (Proposal storage) {
        _ensureProposalExists(proposalId);
        return _proposals[proposalId];
    }

    function _milestoneState(uint256 proposalId, uint8 milestoneIndex) internal view returns (Milestone storage) {
        _ensureProposalExists(proposalId);
        if (milestoneIndex >= _proposalMilestones[proposalId].length) {
            revert InvalidMilestoneIndex(proposalId, milestoneIndex);
        }
        return _proposalMilestones[proposalId][milestoneIndex];
    }

    function _projectState(bytes32 projectId) internal view returns (Project storage) {
        Project storage project = _projects[projectId];
        if (project.projectId == bytes32(0)) {
            revert ProjectNotFound(projectId);
        }
        return project;
    }

    function _ensureProposalExists(uint256 proposalId) internal view {
        if (proposalId == 0 || proposalId >= _nextProposalId) {
            revert ProposalNotFound(proposalId);
        }
    }

    function _readGovernorState(uint256 governorProposalId) internal view returns (IGovernor.ProposalState governorState) {
        if (governorProposalId == 0) {
            revert InvalidGovernorProposalId(0);
        }
        try innovationGovernor.state(governorProposalId) returns (IGovernor.ProposalState currentState) {
            return currentState;
        } catch {
            revert InvalidGovernorProposalId(governorProposalId);
        }
    }

    function _memberView(address account) internal view returns (Member memory) {
        IReputationRegistry.Member memory memberState = reputationRegistry.getMember(account);
        return Member({
            account: account,
            isRegistered: memberState.isRegistered,
            isActive: memberState.isActive,
            currentReputation: memberState.currentReputation
        });
    }
}
