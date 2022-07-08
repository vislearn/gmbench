function wrapper_ipfps(file)

myVars = {'K','Ct','reducedK','offset'};
data = load(file,myVars{:});
offset = data.offset;
K_orig = data.K; % original cost matrix

Ct = data.Ct;
[n1,n2] = size(Ct);
K = - data.reducedK;
num_matches = nnz(Ct);

[nodes,labels] = NodesAndLabels(Ct);

tstart = tic;
fprintf('Start optimization: \n')
fprintf('Model: n1: %g n2: %g \n', n1, n2)

%%% The function already selects the best available solution
[sol, stats]  = spectral_matching_ipfp(K, labels, nodes);

X = zeros(size(Ct));
%%% Cost matrix for LAP
for i = 1:n1
    f = find(nodes == i);
    X(i, labels(f)) = sol(f);
end

X = discretisationMatching_hungarian(full(X),Ct);

curr_score = X(:)' * K_orig * X(:);
fprintf('time: %f ',toc(tstart))
fprintf('upper_bound: %f ', full(curr_score)+cast(offset,'like',full(curr_score)))
indices = 1:n2;
matching = reshape(X,size(Ct))*indices';
fprintf('labeling: [')
fprintf('%g,',matching(1:end-1))
fprintf('%g] \n',matching(end))
