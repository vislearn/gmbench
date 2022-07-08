function wrapper_smac(file)
%%% function to maximize the score vec(X).T K vec(X)
% INPUT
%%% data.K: n1n2*n1n2 cost matrix
%%% data.Ct: n1*n2 binary matrix of feasible matches
%%% data.nodes
%%% data.labels
% OUTPUT
%%% Xs: list of feasible assignments
%%% scores: list of corresponding scores
%%% times: list of corresponding times

myVars = {'K','Ct','reducedK','offset'};
data = load(file,myVars{:});
offset = data.offset;
K_orig = data.K; % original cost matrix

Ct = data.Ct;
[n1,n2] = size(Ct);
K = - data.reducedK;

%%%%%%%% bistochastic normalization
%if options.bn
  %[K,score] = bistocNormalize(sparse(K),1e-7,1000);
%  K = normalizeMatchingW(K,Ct);
%end
tstart = tic;
fprintf('Start optimization: \n')
fprintf('Model: n1: %g n2: %g \n', n1, n2)
%% compute top eigenvectors under affine constraint (matching constraint)
k=3;
%options.constraintMode='both'; %'both' for 1-1 graph matching
%options.isAffine=1;% affine constraint
%options.discretisation=@discretisationGradAssignment; %function for discretization
options.discretisation=@discretisationMatching_hungarian;
[X12,X_SMAC,timing]=compute_graph_matching_SMAC(K,full(Ct),options);
%%% orthonormalize X
%X_SMAC=X(:,:,1);
%X_SMAC=computeXorthonormal(X_SMAC);
%X_SMAC(Ct==0)=0;
%X = X_SMAC;
%%%%%%% discretization with HM
%[matching] = discretizationMatching_hungarian(X,Ct);
%disp(X12)
%disp(X_SMAC)
%ind1 = find(matching);
%ind2 = matching(ind1);
%X = sparse(ind1,ind2,1,n1,n2);

curr_score = X12(:)' * K_orig * X12(:);
fprintf('time: %f ',toc(tstart))
fprintf('upper_bound: %f ', full(curr_score)+cast(offset,'like',full(curr_score)))
indices = 1:n2;
matching = reshape(X12,size(Ct))*indices';
fprintf('labeling: [')
fprintf('%g,',matching(1:end-1))
fprintf('%g] \n',matching(end))
